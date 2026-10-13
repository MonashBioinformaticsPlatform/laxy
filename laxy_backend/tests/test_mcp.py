import json
import os
import shutil
import tempfile
from datetime import timedelta
from urllib.parse import urlparse

from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import AsyncClient, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from laxy_backend.mcp_auth import LaxyTokenVerifier
from laxy_backend.models import (
    AccessToken,
    ComputeResource,
    EventLog,
    File,
    FileSet,
    Job,
    UserApiKey,
)

User = get_user_model()

_META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "0"},
}


def _mcp_body(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    payload_params = dict(params or {})
    payload_params["_meta"] = _META
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": payload_params,
    }


# TransactionTestCase: auth verifier runs ORM in a ThreadPoolExecutor, which
# cannot see uncommitted TestCase transaction rows.
class LaxyTokenVerifierTest(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mcp_user", email="mcp@example.com", password="x"
        )
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.verifier = LaxyTokenVerifier()

    def test_drf_token_accepted(self):
        access = async_to_sync(self.verifier.verify_token)(self.token.key)
        self.assertIsNotNone(access)
        self.assertEqual(access.subject, str(self.user.pk))

    def test_invalid_token_rejected(self):
        access = async_to_sync(self.verifier.verify_token)("not-a-real-token")
        self.assertIsNone(access)

    def test_user_api_key_accepted(self):
        plaintext, _key = UserApiKey.generate(self.user, "mcp-agent")
        access = async_to_sync(self.verifier.verify_token)(plaintext)
        self.assertIsNotNone(access)
        self.assertEqual(access.subject, str(self.user.pk))


@override_settings(MCP_ENABLE_WRITE_TOOLS=False, SECURE_SSL_REDIRECT=False, USE_SSL=False)
class McpEndpointTest(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mcp_owner", email="owner@example.com", password="x"
        )
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.job = Job.objects.create(owner=self.user, status=Job.STATUS_FAILED)
        EventLog.log(
            "JOB_PIPELINE_FAILED", message="boom", user=self.user, obj=self.job
        )
        self.client = AsyncClient()

    async def test_unauthenticated_returns_401(self):
        response = await self.client.post(
            "/api/v1/mcp/",
            data=json.dumps(_mcp_body("tools/list")),
            content_type="application/json",
            headers={
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2026-07-28",
                "Mcp-Method": "tools/list",
            },
        )
        self.assertEqual(response.status_code, 401)

    async def test_tools_list(self):
        response = await self.client.post(
            "/api/v1/mcp/",
            data=json.dumps(_mcp_body("tools/list")),
            content_type="application/json",
            headers={
                "Authorization": f"Bearer {self.token.key}",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2026-07-28",
                "Mcp-Method": "tools/list",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        names = [t["name"] for t in body["result"]["tools"]]
        self.assertIn("laxy_list_jobs", names)
        self.assertIn("laxy_get_job_eventlogs", names)
        self.assertNotIn("laxy_list_compute_resources", names)
        self.assertIn("laxy_diagnose_job", names)
        self.assertIn("laxy_samples_from_ena", names)
        self.assertIn("laxy_revoke_download_tokens", names)
        self.assertIn("laxy_get_job_share", names)

    async def test_list_jobs_and_eventlogs(self):
        auth_headers = {
            "Authorization": f"Bearer {self.token.key}",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2026-07-28",
        }
        response = await self.client.post(
            "/api/v1/mcp/",
            data=json.dumps(
                _mcp_body(
                    "tools/call",
                    {
                        "name": "laxy_list_jobs",
                        "arguments": {"page_size": 5},
                    },
                )
            ),
            content_type="application/json",
            headers={**auth_headers, "Mcp-Method": "tools/call", "Mcp-Name": "laxy_list_jobs"},
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertFalse(body["result"].get("isError"), msg=json.dumps(body)[:2000])
        structured = body["result"].get("structuredContent") or {}
        page = structured.get("result", structured)
        self.assertIn("results", page)
        self.assertIn("total", page)
        self.assertTrue(any(j["id"] == self.job.id for j in page["results"]))

        response = await self.client.post(
            "/api/v1/mcp/",
            data=json.dumps(
                _mcp_body(
                    "tools/call",
                    {
                        "name": "laxy_get_job_eventlogs",
                        "arguments": {"job_id": self.job.id, "page_size": 10},
                    },
                    req_id=2,
                )
            ),
            content_type="application/json",
            headers={
                **auth_headers,
                "Mcp-Method": "tools/call",
                "Mcp-Name": "laxy_get_job_eventlogs",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertFalse(body["result"].get("isError"), msg=json.dumps(body)[:2000])
        structured = body["result"].get("structuredContent") or {}
        events = structured.get("result", structured)
        self.assertIn("results", events)
        self.assertIn("job_url", events)
        self.assertTrue(
            any(e["event"] == "JOB_PIPELINE_FAILED" for e in events["results"])
        )

    async def test_list_compute_resources_omits_extra(self):
        def _prepare():
            staff = User.objects.create_user(
                username="mcp_staff", email="staff@example.com", password="x"
            )
            staff.is_staff = True
            staff.save()
            token, _ = Token.objects.get_or_create(user=staff)
            ComputeResource.objects.create(
                name="secret-host",
                host="secret.example",
                priority=5,
                status=ComputeResource.STATUS_ONLINE,
                extra={
                    "private_key": "SHOULD_NOT_LEAK",
                    "username": "laxy",
                    "queue_type": "slurm",
                },
            )
            return token.key

        key = await sync_to_async(_prepare)()
        response = await self.client.post(
            "/api/v1/mcp/",
            data=json.dumps(
                _mcp_body(
                    "tools/call",
                    {
                        "name": "laxy_list_compute_resources",
                        "arguments": {"page_size": 50},
                    },
                )
            ),
            content_type="application/json",
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2026-07-28",
                "Mcp-Method": "tools/call",
                "Mcp-Name": "laxy_list_compute_resources",
            },
        )
        self.assertEqual(response.status_code, 200)
        raw = response.content.decode()
        self.assertNotIn("SHOULD_NOT_LEAK", raw)
        body = json.loads(response.content)
        self.assertFalse(body["result"].get("isError"), msg=raw[:2000])
        structured = body["result"].get("structuredContent") or {}
        page = structured.get("result", structured)
        row = next(r for r in page["results"] if r["name"] == "secret-host")
        self.assertNotIn("extra", row)
        self.assertEqual(row["host"], "secret.example")
        self.assertEqual(row["queue_type"], "slurm")


@override_settings(
    MCP_JOB_DOWNLOAD_TOKEN_HOURS=1,
    SECURE_SSL_REDIRECT=False,
    USE_SSL=False,
)
class McpDownloadTokenTest(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mcp_dl", email="dl@example.com", password="x"
        )
        content = b"mcp download token test\n"
        self.job_dir = tempfile.mkdtemp()
        fpath = os.path.join(self.job_dir, "run_job.out")
        with open(fpath, "wb") as fh:
            fh.write(content)
        self.file_content = content
        self.fobj = File(
            owner=self.user,
            name=os.path.basename(fpath),
            path=os.path.dirname(fpath),
            location=f"file://{fpath}",
            metadata={"size": len(content)},
        )
        self.fobj.save()
        self.output_files = FileSet()
        self.output_files.add(self.fobj)
        self.output_files.save()
        self.job = Job.objects.create(
            owner=self.user,
            params="{}",
            output_files=self.output_files,
        )

    def tearDown(self):
        shutil.rmtree(self.job_dir, ignore_errors=True)

    def test_minted_url_contains_access_token(self):
        from laxy_backend.mcp import (
            _download_token_payload,
            _file_summary,
            _mint_job_download_token,
        )
        from laxy_backend.models import ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX

        job_token = _mint_job_download_token(
            self.job, self.user, expires_in_seconds=3600
        )
        summary = _file_summary(self.fobj, ctx=None, job_download_token=job_token)
        self.assertIn("access_token=", summary["download_url"])
        self.assertTrue(job_token.token.startswith(ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX))
        meta = _download_token_payload(job_token, expires_in_seconds=3600)
        self.assertIsNotNone(meta["expiry_time"])
        self.assertEqual(meta["access_token"], job_token.token)
        self.assertIsNotNone(job_token.expiry_time)
        job_ct = ContentType.objects.get_for_model(Job)
        self.assertEqual(
            AccessToken.objects.filter(
                object_id=self.job.id, content_type=job_ct
            ).count(),
            1,
        )

    def test_mint_independent_of_share_token(self):
        from laxy_backend.mcp import (
            _download_token_payload,
            _job_access_token,
            _mint_job_download_token,
        )
        from laxy_backend.models import ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX

        job_ct = ContentType.objects.get_for_model(Job)
        share = AccessToken.objects.create(
            object_id=self.job.id,
            content_type=job_ct,
            created_by=self.user,
            expiry_time=None,
        )
        timed_share = AccessToken.objects.create(
            object_id=self.job.id,
            content_type=job_ct,
            created_by=self.user,
            expiry_time=timezone.now() + timedelta(days=7),
        )
        job_token = _mint_job_download_token(
            self.job, self.user, expires_in_seconds=3600
        )
        self.assertTrue(job_token.token.startswith(ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX))
        self.assertNotEqual(job_token.id, share.id)
        self.assertNotEqual(job_token.id, timed_share.id)
        self.assertIsNotNone(job_token.expiry_time)
        meta = _download_token_payload(job_token)
        self.assertIsNotNone(meta["expiry_time"])
        listed_share = _job_access_token(self.job.id)
        self.assertEqual(listed_share.id, share.id)
        self.assertEqual(
            AccessToken.objects.filter(
                object_id=self.job.id, content_type=job_ct
            ).count(),
            3,
        )

    def _add_extra_output_files(self, n: int) -> list[File]:
        added: list[File] = []
        for i in range(n):
            fpath = os.path.join(self.job_dir, f"extra_{i}.out")
            with open(fpath, "wb") as fh:
                fh.write(f"x{i}\n".encode())
            fobj = File(
                owner=self.user,
                name=f"extra_{i}.out",
                path=self.job_dir,
                location=f"file://{fpath}",
                metadata={"size": 3},
            )
            fobj.save()
            self.output_files.add(fobj)
            added.append(fobj)
        self.output_files.save()
        return added

    def test_list_job_files_metadata_only_respects_limit(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import laxy_list_job_files

        self._add_extra_output_files(5)
        with patch("laxy_backend.mcp._current_user", return_value=self.user):
            result = laxy_list_job_files(
                ctx=MagicMock(),
                job_id=self.job.id,
                page_size=3,
            )
        self.assertEqual(result["page_size"], 3)
        self.assertEqual(len(result["results"]), 3)
        self.assertGreaterEqual(result["total"], 6)
        row = result["results"][0]
        self.assertIn("download_path", row)
        self.assertNotIn("download_url", row)
        self.assertNotIn("access_token", result)
        job_ct = ContentType.objects.get_for_model(Job)
        self.assertEqual(
            AccessToken.objects.filter(
                object_id=self.job.id,
                content_type=job_ct,
                token__startswith="mcpdl.",
            ).count(),
            0,
        )

    def test_read_job_file_tail_and_grep(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import laxy_read_job_file

        with patch("laxy_backend.mcp._current_user", return_value=self.user):
            result = laxy_read_job_file(
                ctx=MagicMock(),
                job_id=self.job.id,
                file_path="run_job.out",
                tail_lines=1,
                grep="token",
            )
        self.assertIn("token", result["content"])
        self.assertEqual(result["grep_matches"], 1)
        self.assertNotIn("download_url", result)
        self.assertIn("job_url", result)

    def test_get_download_urls_by_file_id(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import laxy_get_download_urls

        with patch("laxy_backend.mcp._current_user", return_value=self.user):
            result = laxy_get_download_urls(
                ctx=MagicMock(),
                job_id=self.job.id,
                file_ids=[self.fobj.id],
                expires_in_seconds=3600,
            )
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["files"][0]["id"], self.fobj.id)
        self.assertIn("access_token=", result["files"][0]["download_url"])
        self.assertEqual(result["expires_in_seconds"], 3600)
        self.assertIsNotNone(result["expiry_time"])

    def test_revoke_share_leaves_download_token(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import (
            _mint_job_download_token,
            laxy_revoke_job_share,
        )
        from laxy_backend.models import ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX

        job_ct = ContentType.objects.get_for_model(Job)
        share = AccessToken.objects.create(
            object_id=self.job.id,
            content_type=job_ct,
            created_by=self.user,
            expiry_time=None,
        )
        dl = _mint_job_download_token(
            self.job, self.user, expires_in_seconds=3600
        )
        with (
            patch("laxy_backend.mcp._current_user", return_value=self.user),
            patch("laxy_backend.mcp._write_tools_enabled", return_value=True),
        ):
            revoked = laxy_revoke_job_share(ctx=MagicMock(), job_id=self.job.id)
        self.assertTrue(revoked["share_revoked"])
        self.assertEqual(revoked["share_token_id"], share.id)
        dl.refresh_from_db()
        self.assertTrue(dl.token.startswith(ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX))
        self.assertTrue(AccessToken.objects.filter(id=dl.id).exists())
        self.assertFalse(AccessToken.objects.filter(id=share.id).exists())

    def test_revoke_download_tokens_option(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import (
            _mint_job_download_token,
            laxy_revoke_download_tokens,
        )

        dl = _mint_job_download_token(
            self.job, self.user, expires_in_seconds=3600
        )
        with (
            patch("laxy_backend.mcp._current_user", return_value=self.user),
            patch("laxy_backend.mcp._write_tools_enabled", return_value=True),
        ):
            revoked = laxy_revoke_download_tokens(
                ctx=MagicMock(),
                job_id=self.job.id,
            )
        self.assertIn(str(dl.id), revoked["download_tokens_revoked"])
        self.assertFalse(AccessToken.objects.filter(id=dl.id).exists())

    def test_clone_treats_200_as_success(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import laxy_clone_job

        body = {
            "pipelinerun_id": "pr1",
            "samplecart_id": "sc1",
            "pipeline": "nf-core-rnaseq",
        }
        with (
            patch("laxy_backend.mcp._current_user", return_value=self.user),
            patch("laxy_backend.mcp._write_tools_enabled", return_value=True),
            patch("laxy_backend.mcp._job_for_user", return_value=self.job),
            patch("laxy_backend.mcp._call_api_view", return_value=(200, body)),
        ):
            result = laxy_clone_job(ctx=MagicMock(), job_id=self.job.id)
        self.assertEqual(result["pipelinerun_id"], "pr1")
        self.assertEqual(result["samplecart_id"], "sc1")
        hint = result["next_step"]
        self.assertIn("laxy_get_pipeline_run(pipeline_run_id='pr1')", hint)
        self.assertIn("laxy_get_sample_cart(sample_cart_id='sc1')", hint)
        self.assertIn("laxy_update_pipeline_run(pipeline_run_id='pr1'", hint)
        self.assertIn("laxy_update_sample_cart(sample_cart_id='sc1'", hint)
        self.assertIn("laxy_start_job(pipeline_run_id='pr1')", hint)

    def test_download_ttl_capped_at_max_hours(self):
        from laxy_backend.mcp import _mint_job_download_token

        with override_settings(MCP_JOB_DOWNLOAD_TOKEN_MAX_HOURS=3):
            token = _mint_job_download_token(
                self.job, self.user, expires_in_seconds=99 * 3600
            )
        remaining = token.expiry_time - timezone.now()
        self.assertLessEqual(remaining.total_seconds(), 3 * 3600 + 5)

    def test_token_reused_for_multiple_files(self):
        from laxy_backend.mcp import _file_summary, _mint_job_download_token

        fpath2 = os.path.join(self.job_dir, "other.out")
        with open(fpath2, "wb") as fh:
            fh.write(b"second\n")
        fobj2 = File(
            owner=self.user,
            name="other.out",
            path=self.job_dir,
            location=f"file://{fpath2}",
            metadata={"size": 7},
        )
        fobj2.save()
        self.output_files.add(fobj2)

        first = _mint_job_download_token(self.job, self.user)
        _file_summary(self.fobj, ctx=None, job_download_token=first)
        second = _mint_job_download_token(self.job, self.user)
        _file_summary(fobj2, ctx=None, job_download_token=second)
        self.assertEqual(first.id, second.id)
        job_ct = ContentType.objects.get_for_model(Job)
        self.assertEqual(
            AccessToken.objects.filter(
                object_id=self.job.id, content_type=job_ct
            ).count(),
            1,
        )

    def test_unauthenticated_download_with_job_token(self):
        from laxy_backend.mcp import _file_download_url, _mint_job_download_token

        job_token = _mint_job_download_token(self.job, self.user)
        url = _file_download_url(self.fobj, ctx=None, access_token=job_token.token)
        path = urlparse(url).path
        query = urlparse(url).query
        client = APIClient()
        response = client.get(f"{path}?{query}")
        self.assertEqual(response.status_code, 200)
        body = b"".join(response.streaming_content)
        self.assertEqual(body, self.file_content)

    def test_job_accesstoken_endpoint_ignores_mcpdl(self):
        from laxy_backend.mcp import _mint_job_download_token
        from laxy_backend.models import ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX

        dl = _mint_job_download_token(self.job, self.user)
        self.assertTrue(dl.token.startswith(ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX))
        url = reverse(
            "laxy_backend:job_accesstoken", args=[self.job.id]
        )
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get(url)
        self.assertEqual(response.status_code, 204)

        job_ct = ContentType.objects.get_for_model(Job)
        share = AccessToken.objects.create(
            object_id=self.job.id,
            content_type=job_ct,
            created_by=self.user,
            expiry_time=None,
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token"], share.token)
        self.assertFalse(
            response.data["token"].startswith(ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX)
        )

    def test_download_rejects_expired_token(self):
        from laxy_backend.models import generate_mcp_download_access_token_string

        job_ct = ContentType.objects.get_for_model(Job)
        expired = AccessToken.objects.create(
            object_id=self.job.id,
            content_type=job_ct,
            created_by=self.user,
            token=generate_mcp_download_access_token_string(),
            expiry_time=timezone.now() - timedelta(hours=1),
        )
        path = reverse(
            "laxy_backend:file_download",
            kwargs={"uuid": self.fobj.uuid(), "filename": self.fobj.name},
        )
        client = APIClient()
        response = client.get(f"{path}?access_token={expired.token}")
        self.assertIn(response.status_code, (401, 403, 404))

    def test_download_rejects_missing_token_when_anonymous(self):
        path = reverse(
            "laxy_backend:file_download",
            kwargs={"uuid": self.fobj.uuid(), "filename": self.fobj.name},
        )
        client = APIClient()
        response = client.get(path)
        self.assertIn(response.status_code, (401, 403, 404))

    def test_normalize_samples_merges_single_key_lanes(self):
        from laxy_backend.mcp import _normalize_samples, _samples_from_ena_runs

        samples = _normalize_samples(
            [
                {
                    "name": "wt",
                    "files": [{"R1": "http://r1"}, {"R2": "http://r2"}],
                }
            ]
        )
        self.assertEqual(samples[0]["files"], [{"R1": "http://r1", "R2": "http://r2"}])
        built = _samples_from_ena_runs(
            {
                "SRR1": {
                    "sample_alias": "wt",
                    "fastq_ftp": [{"R1": "http://a"}, {"R2": "http://b"}],
                }
            }
        )
        self.assertEqual(built[0]["name"], "wt")
        self.assertEqual(built[0]["files"][0]["R1"], "http://a")

    def test_diagnose_job_includes_log_tail(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import laxy_diagnose_job

        with patch("laxy_backend.mcp._current_user", return_value=self.user):
            result = laxy_diagnose_job(ctx=MagicMock(), job_id=self.job.id, tail_lines=5)
        self.assertIn("job_url", result)
        self.assertIn("mcp download token test", result["log"]["content"])

    def test_submit_dry_run_does_not_create_a_job(self):
        from unittest.mock import MagicMock, patch

        from laxy_backend.mcp import laxy_submit_job

        before = Job.objects.count()
        with patch("laxy_backend.mcp._current_user", return_value=self.user):
            result = laxy_submit_job(
                ctx=MagicMock(),
                pipeline_name="not-a-pipeline",
                pipeline_version="0",
                samples=[{"name": "s", "files": [{"R1": "http://example/r1.fastq.gz"}]}],
                dry_run=True,
            )
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["valid"])
        self.assertEqual(Job.objects.count(), before)
