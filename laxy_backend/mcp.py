"""Laxy MCP 2.0 (stateless 2026-07-28) tools.

Mounted at ``/api/v1/mcp/`` via ``django_stateless_mcp.mcp_view``.
"""

from __future__ import annotations

import fnmatch
import io
import json
import logging
import os
import re
from datetime import timedelta
from typing import Annotated, Any
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user
from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema
from rest_framework.test import APIRequestFactory, force_authenticate

from django_stateless_mcp import django_request, request_state_security
from laxy_backend.mcp_auth import LaxyTokenVerifier
from laxy_backend.models import (
    ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX,
    AccessToken,
    ComputeResource,
    EventLog,
    File,
    Job,
    Pipeline,
    PipelineRun,
    SampleCart,
    generate_mcp_download_access_token_string,
    get_compute_resource_str_for_location,
)
from laxy_backend.views import (
    AccessTokenView,
    ENAFastqUrlQueryView,
    ENAQueryView,
    JobAccessTokenView,
    JobClone,
    JobCreate,
    JobView,
    PipelineRunCreate,
    PipelineRunView,
    RemoteBrowseView,
    SampleCartCreate,
    SampleCartView,
    SendFileToDegust,
)
from laxy_backend.serializers import ComputeResourceListSerializer
from laxy_genomes.data.genomes import reference_genomes_for_api

logger = logging.getLogger(__name__)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
# Creates or queues work that is not a simple field edit.
DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False
)
# Mutates records without cancelling a job or deleting tokens.
WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False
)

JOB_STATUSES = (
    "created",
    "hold",
    "starting",
    "running",
    "failed",
    "cancelled",
    "complete",
)
# Top-level enum plus null. Optional Literal becomes anyOf, and some clients
# drop the enum when they flatten that to string|null.
JOB_STATUS_SCHEMA = {
    "type": ["string", "null"],
    "enum": [*JOB_STATUSES, None],
    "default": None,
    "description": (
        "Exact job status. Omit or null for every status. "
        "Values: created, hold, starting, running, failed, cancelled, complete."
    ),
}


class SampleLane(BaseModel):
    """One lane or technical replicate.

    ``R1`` and optional ``R2`` sit on the same object. A list of single-key
    dicts (``[{R1: url}, {R2: url}]``, the ENA fastq_ftp shape) is accepted
    by the normaliser and merged into this shape before save.
    """

    model_config = ConfigDict(extra="allow")
    R1: str = Field(description="Read 1 URL, file id, or remote path")
    R2: str | None = Field(
        default=None, description="Read 2 URL when the lane is paired-end"
    )


class SampleSpec(BaseModel):
    """One biological sample. ``files`` is one entry per lane."""

    model_config = ConfigDict(extra="allow")
    name: str = Field(description="Sample name")
    files: list[SampleLane] = Field(
        description=(
            "Lanes for this sample. Each lane is {R1, R2?}, not a list of "
            "single-key dicts."
        )
    )

# Tools in this set are omitted from tools/list unless the bearer is a Django
# staff user (REST IsAdminUser). Calls are rejected again inside the handler.
ADMIN_MCP_TOOLS = frozenset({"laxy_list_compute_resources"})


def _is_rest_admin(user) -> bool:
    """Same gate as DRF ``IsAdminUser``: authenticated and ``is_staff``."""
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_staff", False)
    )


def _user_from_list_context(ctx) -> Any:
    """Django user during tools/list, if the request came through mcp_view."""
    request = getattr(ctx, "request", None)
    state = getattr(request, "state", None)
    http_request = getattr(state, "django_request", None)
    if http_request is None and state is not None:
        getter = getattr(state, "get", None)
        if callable(getter):
            http_request = getter("django_request")
    return getattr(http_request, "user", None)


class LaxyMCPServer(MCPServer):
    async def _handle_list_tools(self, ctx, params):  # type: ignore[override]
        from mcp.types import ListToolsResult

        tools = await self.list_tools()
        if not _is_rest_admin(_user_from_list_context(ctx)):
            tools = [tool for tool in tools if tool.name not in ADMIN_MCP_TOOLS]
        return ListToolsResult(tools=tools)

    async def call_tool(self, name, arguments, context=None):  # type: ignore[override]
        if name in ADMIN_MCP_TOOLS:
            user = None
            if context is not None:
                try:
                    user = django_request(context).user
                except Exception:
                    user = None
            if not _is_rest_admin(user):
                raise PermissionError(
                    "Admin only. This tool requires a staff user, "
                    "the same check as the REST compute-resource API."
                )
        return await super().call_tool(name, arguments, context)

# Do not open remote storage for files larger than this when inlining content —
# MCP client timeouts are typically ~30–60s; large SFTP streams often exceed that.
_INLINE_SIZE_LIMIT = 256 * 1024

# Reuse an existing job download token if it still has at least this long left.
_JOB_DOWNLOAD_TOKEN_REUSE_REMAINING = timedelta(minutes=30)

token_verifier = LaxyTokenVerifier()

server = LaxyMCPServer(
    name="laxy",
    version="1.3.0",
    request_state_security=request_state_security(),
    instructions=(
        "Laxy genomics job management. Read tools are readOnlyHint; "
        "cancel/revoke/submit/start are destructiveHint. Write tools require "
        "LAXY_MCP_ENABLE_WRITE_TOOLS.\n\n"
        "Diagnose a failed job with laxy_diagnose_job (status, recent events, "
        "tail of output/run_job.out). For a specific file use "
        "laxy_read_job_file with tail_lines and/or grep. "
        "laxy_list_job_files is metadata only. Downloads are only "
        "laxy_get_download_urls or laxy_get_job_tarball_urls (mcpdl.* tokens, "
        "not UI share links). Curl those URLs without the MCP bearer token. "
        "Revoke download tokens with laxy_revoke_download_tokens, and the UI "
        "share link with laxy_revoke_job_share.\n\n"
        "Lists use page and page_size (no limit alias). "
        "laxy_list_compute_resources is staff-only and is omitted from "
        "tools/list unless the MCP token user is Django is_staff.\n\n"
        "Submit: laxy_list_pipelines returns versions and params_schema; "
        "samples are {name, files: [{R1, R2?}]}. Pass dry_run=true on "
        "laxy_submit_job or laxy_start_job to validate without queueing. "
        "laxy_samples_from_ena builds that samples list from accessions.\n\n"
        "Re-run: laxy_clone_job(job_id, start=false) copies SampleCart + "
        "PipelineRun only. Optional params/samples overrides, then "
        "start=true (or laxy_start_job) creates the Job. "
        "Read the UI share with laxy_get_job_share. Mint or update it with "
        "laxy_share_job. Revoke it with laxy_revoke_job_share."
    ),
)


def _current_user(ctx: Context):
    request = django_request(ctx)
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionError("Authentication required")
    return user


def _job_for_user(user, job_id: str) -> Job:
    try:
        job = Job.objects.select_related(
            "owner", "compute_resource", "input_files", "output_files"
        ).get(id=job_id)
    except Job.DoesNotExist as exc:
        raise LookupError(f"Unknown job ID: {job_id}") from exc
    if not user.is_superuser and job.owner_id != user.pk:
        raise PermissionError(f"No access to job {job_id}")
    return job


def _pipelinerun_for_user(user, pipelinerun_id: str) -> PipelineRun:
    try:
        run = PipelineRun.objects.select_related("owner", "sample_cart").get(
            id=pipelinerun_id
        )
    except PipelineRun.DoesNotExist as exc:
        raise LookupError(f"Unknown pipeline run ID: {pipelinerun_id}") from exc
    if not user.is_superuser and run.owner_id != user.pk:
        raise PermissionError(f"No access to pipeline run {pipelinerun_id}")
    return run


def _samplecart_for_user(user, samplecart_id: str) -> SampleCart:
    try:
        cart = SampleCart.objects.select_related("owner").get(id=samplecart_id)
    except SampleCart.DoesNotExist as exc:
        raise LookupError(f"Unknown sample cart ID: {samplecart_id}") from exc
    if not user.is_superuser and cart.owner_id != user.pk:
        raise PermissionError(f"No access to sample cart {samplecart_id}")
    return cart


def _api_base_url(ctx: Context | None = None) -> str:
    """Public API origin for download links (no trailing slash)."""
    configured = (getattr(settings, "FRONTEND_API_URL", None) or "").rstrip("/")
    if configured:
        return configured
    if ctx is not None:
        request = django_request(ctx)
        return request.build_absolute_uri("/").rstrip("/")
    return ""


def _frontend_base_url(ctx: Context | None = None) -> str:
    """Public web UI origin for share links (no trailing slash)."""
    configured = (
        getattr(settings, "FRONTEND_URL", None)
        or os.environ.get("LAXY_FRONTEND_URL")
        or ""
    ).rstrip("/")
    if configured:
        return configured
    api = _api_base_url(ctx)
    if api.endswith(":8001"):
        return f"{api[:-5]}:8002"
    return api or "http://localhost:8002"


def _job_ui_url(job_id: str, ctx: Context | None = None) -> str:
    return f"{_frontend_base_url(ctx)}/#/job/{job_id}/"


def _attach_job_url(payload: dict[str, Any], job_id: str, ctx: Context | None) -> dict[str, Any]:
    payload["job_id"] = payload.get("job_id") or job_id
    payload["job_url"] = _job_ui_url(str(payload["job_id"]), ctx)
    return payload


_READ_KEYS = ("R1", "R2", "I1", "I2")


def _normalize_samples(samples: list[Any]) -> list[dict[str, Any]]:
    """Coerce samples to ``{name, files: [{R1, R2?}]}``.

    Merges a lane written as ``[{R1: url}, {R2: url}]`` into one object.
    """
    normalised: list[dict[str, Any]] = []
    for sample in samples or []:
        if hasattr(sample, "model_dump"):
            sample = sample.model_dump(exclude_none=True)
        if not isinstance(sample, dict):
            raise ValueError(
                f"Each sample must be an object, got {type(sample).__name__}"
            )
        name = sample.get("name")
        if not name:
            raise ValueError("Each sample needs a name")
        raw_files = sample.get("files") or []
        if not isinstance(raw_files, list) or not raw_files:
            raise ValueError(f"Sample {name!r} needs a non-empty files list")
        lanes: list[dict[str, Any]] = []
        pending: dict[str, Any] | None = None
        for entry in raw_files:
            if hasattr(entry, "model_dump"):
                entry = entry.model_dump(exclude_none=True)
            if not isinstance(entry, dict):
                raise ValueError(f"Sample {name!r} files must be objects")
            lane = {
                k: entry[k]
                for k in entry
                if entry.get(k) is not None
            }
            if "R1" not in lane and "R2" not in lane:
                raise ValueError(f"Sample {name!r} lane needs R1 (and optional R2)")
            if "R1" in lane and "R2" in lane:
                if pending:
                    lanes.append(pending)
                    pending = None
                lanes.append(lane)
                continue
            if "R1" in lane:
                if pending:
                    lanes.append(pending)
                pending = lane
                continue
            if pending and "R1" in pending:
                pending.update(lane)
                lanes.append(pending)
                pending = None
                continue
            raise ValueError(f"Sample {name!r} has an R2 lane without an R1")
        if pending:
            lanes.append(pending)
        extra = {k: v for k, v in sample.items() if k not in ("name", "files")}
        normalised.append({"name": name, "files": lanes, **extra})
    if not normalised:
        raise ValueError("samples must contain at least one sample")
    return normalised


def _pipeline_public_row(pipeline: Pipeline) -> dict[str, Any]:
    meta = pipeline.metadata or {}
    versions = meta.get("versions") or []
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "owner": pipeline.owner.get_username() if pipeline.owner else None,
        "public": pipeline.public,
        "created_time": (
            pipeline.created_time.isoformat() if pipeline.created_time else None
        ),
        "versions": versions,
        "default_version": meta.get("default_version"),
        "short_description": meta.get("short_description"),
        "params_schema": meta.get("params_schema"),
        "param_defaults": meta.get("param_defaults") or meta.get("defaults"),
    }


def _prune_to_fields(obj: Any, fields: set[str]) -> Any:
    """Keep dict keys in ``fields`` and any ancestor that still has matches."""
    wanted = {f.lower() for f in fields}
    if isinstance(obj, list):
        kept = [_prune_to_fields(item, fields) for item in obj]
        return [item for item in kept if item not in (None, {}, [])]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if str(key).lower() in wanted:
                out[key] = value
                continue
            pruned = _prune_to_fields(value, fields)
            if pruned not in (None, {}, []):
                out[key] = pruned
        return out
    return None


def _samples_from_ena_runs(runs: dict[str, Any]) -> list[dict[str, Any]]:
    """Group an ENA run table into submit_job samples."""
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for run_acc, meta in (runs or {}).items():
        if not isinstance(meta, dict):
            continue
        sample_name = (
            meta.get("sample_alias")
            or meta.get("library_name")
            or meta.get("sample_accession")
            or run_acc
        )
        sample_name = str(sample_name)
        lane: dict[str, str] = {}
        for item in meta.get("fastq_ftp") or []:
            if isinstance(item, dict):
                for key, url in item.items():
                    if url:
                        lane[str(key)] = str(url)
            elif isinstance(item, str) and item:
                key = "R1" if "R1" not in lane else "R2"
                lane[key] = item
        if "R1" not in lane:
            continue
        if sample_name not in grouped:
            grouped[sample_name] = {"name": sample_name, "files": []}
            order.append(sample_name)
        grouped[sample_name]["files"].append(lane)
    return [grouped[name] for name in order]


_DEFAULT_DOWNLOAD_TTL_SECONDS = 3600
# Schema / docs cap (runtime also respects LAXY_MCP_JOB_DOWNLOAD_TOKEN_MAX_HOURS).
_SCHEMA_MAX_DOWNLOAD_TTL_SECONDS = 3 * 3600
_MAX_DOWNLOAD_URL_FILES = 200


def _job_download_token_max_seconds() -> int:
    hours = int(getattr(settings, "MCP_JOB_DOWNLOAD_TOKEN_MAX_HOURS", 3) or 3)
    return max(60, min(hours, 72) * 3600)


def _job_download_token_ttl(
    expires_in_seconds: int | None = None,
) -> timedelta:
    max_secs = _job_download_token_max_seconds()
    if expires_in_seconds is not None:
        secs = max(60, min(int(expires_in_seconds), max_secs))
        return timedelta(seconds=secs)
    hours = int(getattr(settings, "MCP_JOB_DOWNLOAD_TOKEN_HOURS", 1) or 1)
    return timedelta(seconds=max(60, min(hours * 3600, max_secs)))


def _paginate(items: list[Any], page: int, page_size: int) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 200))
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "results": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1 and total > 0,
    }


def _paginate_queryset(qs: QuerySet, page: int, page_size: int) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 200))
    total = qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
    start = (page - 1) * page_size
    slice_qs = qs[start : start + page_size]
    return {
        "results": list(slice_qs),
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1 and total > 0,
    }


def _job_share_payload(
    token_obj: AccessToken | None, job_id: str, ctx: Context | None = None
) -> dict[str, Any]:
    if token_obj is None:
        return {
            "job_id": job_id,
            "token": None,
            "token_id": None,
            "expiry_time": None,
            "share_url": None,
            "active": False,
        }
    frontend = _frontend_base_url(ctx)
    share_url = f"{frontend}/#/job/{job_id}/?access_token={token_obj.token}"
    expired = bool(
        token_obj.expiry_time and token_obj.expiry_time <= timezone.now()
    )
    return {
        "job_id": job_id,
        "token": token_obj.token,
        "token_id": token_obj.id,
        "expiry_time": (
            token_obj.expiry_time.isoformat() if token_obj.expiry_time else None
        ),
        "share_url": share_url,
        "active": not expired,
    }


def _job_access_token_ct() -> ContentType:
    return ContentType.objects.get_for_model(Job)


def _mint_job_download_token(
    job: Job,
    user,
    expires_in_seconds: int | None = None,
) -> AccessToken:
    """
    Job-scoped AccessToken for ``?access_token=`` on file download URLs.

    Tokens use the ``mcpdl.`` prefix so they are distinct from UI share
    tokens. REST accepts them via ``FileHasAccessTokenForJob``.
    """
    ct = _job_access_token_ct()
    now = timezone.now()
    ttl = _job_download_token_ttl(expires_in_seconds)
    force_refresh = expires_in_seconds is not None
    min_expiry = now + _JOB_DOWNLOAD_TOKEN_REUSE_REMAINING
    base_qs = AccessToken.objects.filter(
        object_id=job.id,
        content_type=ct,
        created_by=user,
        token__startswith=ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX,
    )
    if not force_refresh:
        obj = (
            base_qs.filter(expiry_time__gt=min_expiry)
            .order_by("expiry_time")
            .first()
        )
        if obj is not None:
            return obj
    obj = base_qs.order_by("-expiry_time").first()
    if obj is not None:
        obj.expiry_time = now + ttl
        obj.save(update_fields=["expiry_time", "modified_time"])
        return obj
    return AccessToken.objects.create(
        object_id=job.id,
        content_type=ct,
        created_by=user,
        token=generate_mcp_download_access_token_string(),
        expiry_time=now + ttl,
    )


def _file_download_path(fobj: File) -> str:
    return fobj.get_absolute_url()


def _file_download_url(
    fobj: File,
    ctx: Context | None,
    access_token: str,
) -> str:
    base = _api_base_url(ctx)
    path = _file_download_path(fobj)
    query = urlencode({"access_token": access_token})
    absolute = f"{base}{path}" if base else path
    return f"{absolute}?{query}"


def _archive_compute_ids() -> set[str]:
    return {
        str(i)
        for i in ComputeResource.objects.exclude(archive_host_id=None).values_list(
            "archive_host_id", flat=True
        )
        if i
    }


def _file_availability(fobj: File, archive_ids: set[str] | None = None) -> str:
    """``online`` for live compute storage, ``archive`` when the default location is an archive host."""
    try:
        url = str(fobj.location or "")
    except Exception:
        return "unknown"
    if not url:
        return "unknown"
    compute_id = get_compute_resource_str_for_location(url)
    if compute_id and archive_ids and str(compute_id) in archive_ids:
        return "archive"
    return "online"


def _file_metadata(
    fobj: File, archive_ids: set[str] | None = None
) -> dict[str, Any]:
    return {
        "id": fobj.id,
        "path": fobj.path,
        "name": fobj.name,
        "full_path": fobj.full_path,
        "checksum": fobj.checksum,
        "size": (fobj.metadata or {}).get("size"),
        "type_tags": fobj.type_tags or [],
        "fileset_id": fobj.fileset_id,
        "download_path": _file_download_path(fobj),
        "availability": _file_availability(fobj, archive_ids),
    }


def _file_summary(
    fobj: File,
    ctx: Context | None,
    job_download_token: AccessToken,
    archive_ids: set[str] | None = None,
) -> dict[str, Any]:
    summary = _file_metadata(fobj, archive_ids)
    summary["download_url"] = _file_download_url(
        fobj, ctx, job_download_token.token
    )
    return summary


def _download_token_payload(
    token: AccessToken,
    ctx: Context | None = None,
    *,
    expires_in_seconds: int | None = None,
) -> dict[str, Any]:
    max_secs = _job_download_token_max_seconds()
    return {
        "access_token": token.token,
        "expiry_time": (
            token.expiry_time.isoformat() if token.expiry_time else None
        ),
        "expires_in_seconds": expires_in_seconds,
        "max_expires_in_seconds": max_secs,
        "api_base_url": _api_base_url(ctx) or None,
        "download_access_token_scope": "job",
        "download_access_token_note": (
            "Short-lived job-scoped mcpdl.* token (not the UI share link). "
            f"TTL capped at {max_secs}s. After downloads finish, revoke with "
            "laxy_revoke_download_tokens(job_id). "
            "Download with curl -f so HTTP errors are not saved as the file: "
            "curl -fL -o <name> '<download_url>'. Archive/offline files can "
            "504 while staging; check availability before downloading."
        ),
        "revoke_after_download": (
            "Call laxy_revoke_download_tokens(job_id) once downloads are complete."
        ),
    }


def _revoke_mcp_download_tokens(job_id: str, user) -> list[str]:
    """Delete all mcpdl.* download tokens for this job created by user."""
    ct = _job_access_token_ct()
    qs = AccessToken.objects.filter(
        object_id=job_id,
        content_type=ct,
        created_by=user,
        token__startswith=ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX,
    )
    ids = list(qs.values_list("id", flat=True))
    qs.delete()
    return [str(i) for i in ids]


def _collect_job_files(job: Job, which: str = "both") -> list[File]:
    which_l = (which or "both").lower()
    files: list[File] = []
    if which_l in ("input", "both") and job.input_files_id:
        files.extend(list(job.input_files.get_files()))
    if which_l in ("output", "both") and job.output_files_id:
        files.extend(list(job.output_files.get_files()))
    return files


def _select_job_files_for_download(
    job: Job,
    *,
    which: str = "both",
    file_ids: list[str] | None = None,
    paths: list[str] | None = None,
    path_glob: str | None = None,
    path_prefix: str | None = None,
    limit: int = _MAX_DOWNLOAD_URL_FILES,
) -> list[File]:
    if not any([file_ids, paths, path_glob, path_prefix]):
        raise ValueError(
            "Provide at least one of: file_ids, paths, path_glob, path_prefix"
        )
    limit = max(1, min(int(limit), _MAX_DOWNLOAD_URL_FILES))
    selected: list[File] = []
    seen: set[str] = set()

    def _add(fobj: File) -> None:
        if fobj.id not in seen:
            seen.add(fobj.id)
            selected.append(fobj)

    if file_ids:
        id_set = {str(i) for i in file_ids}
        for fobj in _collect_job_files(job, which):
            if fobj.id in id_set:
                _add(fobj)
        missing = id_set - seen
        if missing:
            raise LookupError(
                f"File id(s) not found on job {job.id}: "
                f"{', '.join(sorted(missing))}"
            )

    if paths:
        for p in paths:
            _add(_resolve_job_file(job, p))

    if path_glob or path_prefix:
        prefix = (path_prefix or "").lstrip("/")
        for fobj in _collect_job_files(job, which):
            rel = (
                f"{fobj.path}/{fobj.name}".lstrip("/")
                if fobj.path
                else (fobj.name or "")
            )
            if prefix and not (
                rel.startswith(prefix) or (fobj.path or "").startswith(prefix)
            ):
                continue
            if path_glob and not fnmatch.fnmatch(rel, path_glob):
                continue
            _add(fobj)

    return selected[:limit]


def _job_summary(job: Job, ctx: Context | None = None) -> dict[str, Any]:
    latest = job.latest_event()
    params = job.params or {}
    if isinstance(params, str):
        try:
            params = json.loads(params) or {}
        except json.JSONDecodeError:
            params = {}
    if not isinstance(params, dict):
        params = {}
    nested = params.get("params") or {}
    if not isinstance(nested, dict):
        nested = {}
    sample_cart = params.get("sample_cart") or {}
    samples = sample_cart.get("samples") or []
    return {
        "id": job.id,
        "job_url": _job_ui_url(job.id, ctx),
        "status": job.status,
        "exit_code": job.exit_code,
        "owner": job.owner.get_username() if job.owner else None,
        "pipeline": params.get("pipeline"),
        "pipeline_version": nested.get("pipeline_version"),
        "description": params.get("description") or nested.get("description"),
        "genome": nested.get("genome") or params.get("genome"),
        "sample_count": len(samples) if isinstance(samples, list) else None,
        "compute_resource": job.compute_resource_id,
        "created_time": job.created_time.isoformat() if job.created_time else None,
        "completed_time": (
            job.completed_time.isoformat() if job.completed_time else None
        ),
        "latest_event": getattr(latest, "event", None) if latest else None,
    }


@server.tool(
    name="laxy_list_jobs",
    description=(
        "List jobs owned by the authenticated user (or all jobs for superusers). "
        "Paginate with page (1-based) and page_size (max 200; default 10). "
        "Filters: status (schema enum: created, hold, starting, running, "
        "failed, cancelled, complete), pipeline, search. Each row includes job_url."
    ),
    annotations=READ_ONLY,
)
def laxy_list_jobs(
    ctx: Context,
    status: Annotated[
        str | None,
        WithJsonSchema(JOB_STATUS_SCHEMA),
    ] = None,
    pipeline: Annotated[
        str | None, Field(description="Filter by pipeline name (substring)")
    ] = None,
    search: Annotated[
        str | None,
        Field(description="Free-text match on job id, description, or remote_id"),
    ] = None,
    page: Annotated[int, Field(description="1-based page number", ge=1)] = 1,
    page_size: Annotated[
        int, Field(description="Results per page (max 200)", ge=1, le=200)
    ] = 10,
) -> dict[str, Any]:
    user = _current_user(ctx)
    qs = Job.objects.select_related(
        "owner", "compute_resource"
    ).order_by("-created_time")
    if not user.is_superuser:
        qs = qs.filter(owner=user)
    if status:
        if status not in JOB_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(JOB_STATUSES)}"
            )
        qs = qs.filter(status=status)
    if pipeline:
        qs = qs.filter(params__pipeline__icontains=pipeline)
    if search:
        term = search.strip()
        if term:
            qs = qs.filter(
                Q(id__icontains=term)
                | Q(remote_id__icontains=term)
                | Q(params__description__icontains=term)
                | Q(params__params__description__icontains=term)
            )
    page_data = _paginate_queryset(qs, page, page_size)
    page_data["results"] = [_job_summary(job, ctx) for job in page_data["results"]]
    return page_data


@server.tool(
    name="laxy_get_job",
    description=(
        "Get details for a single Laxy job by ID, including job_url. "
        "For a failed job, prefer laxy_diagnose_job (status + events + log tail)."
    ),
    annotations=READ_ONLY,
)
def laxy_get_job(
    ctx: Context,
    job_id: str,
    include_log_tail: Annotated[
        bool,
        Field(description="If true, include the tail of output/run_job.out"),
    ] = False,
    tail_lines: Annotated[
        int, Field(description="Lines of the main log when include_log_tail", ge=1, le=500)
    ] = 50,
) -> dict[str, Any]:
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    summary = _job_summary(job, ctx)
    summary["params"] = job.params or {}
    summary["metadata"] = job.metadata or {}
    summary["input_fileset_id"] = job.input_files_id
    summary["output_fileset_id"] = job.output_files_id
    summary["remote_id"] = job.remote_id
    if include_log_tail:
        summary["log"] = _main_log_tail(job, tail_lines=tail_lines)
    return summary


def _event_row(event: EventLog) -> dict[str, Any]:
    return {
        "id": event.id,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "event": event.event,
        "message": event.message,
        "extra": event.extra or {},
    }


@server.tool(
    name="laxy_get_job_eventlogs",
    description=(
        "List event-log entries for a job (status changes, pipeline messages). "
        "Paginate with page and page_size, or pass offset (0-based) to skip "
        "rows. event filters by event name substring (EventLog has no separate "
        "level field), e.g. FAILED or JOB_STATUS_CHANGED. Includes job_url."
    ),
    annotations=READ_ONLY,
)
def laxy_get_job_eventlogs(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
    page: Annotated[int, Field(description="1-based page number", ge=1)] = 1,
    page_size: Annotated[
        int, Field(description="Results per page (max 200)", ge=1, le=200)
    ] = 50,
    offset: Annotated[
        int | None,
        Field(description="0-based row offset. When set, overrides page."),
    ] = None,
    event: Annotated[
        str | None,
        Field(
            description=(
                "Substring filter on the event name (the log category), "
                "e.g. FAILED or JOB_STATUS_CHANGED"
            )
        ),
    ] = None,
) -> dict[str, Any]:
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    qs = EventLog.objects.filter(object_id=job.id).order_by("-timestamp")
    if event:
        qs = qs.filter(event__icontains=event.strip())
    if offset is not None:
        offset = max(0, int(offset))
        page_size = max(1, min(int(page_size), 200))
        total = qs.count()
        rows = list(qs[offset : offset + page_size])
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
        page = (offset // page_size) + 1
        page_data = {
            "results": rows,
            "page": page,
            "page_size": page_size,
            "offset": offset,
            "total": total,
            "total_pages": total_pages,
            "has_next": offset + page_size < total,
            "has_previous": offset > 0,
        }
    else:
        page_data = _paginate_queryset(qs, page, page_size)
        page_data["offset"] = (page_data["page"] - 1) * page_data["page_size"]
    page_data["results"] = [_event_row(e) for e in page_data["results"]]
    page_data["job_id"] = job.id
    page_data["job_url"] = _job_ui_url(job.id, ctx)
    page_data["event"] = event
    return page_data


def _filter_file_queryset(
    qs: QuerySet,
    *,
    extension: str | None = None,
    path_prefix: str | None = None,
    name_glob: str | None = None,
    path_glob: str | None = None,
    path_regex: str | None = None,
) -> list[File]:
    if extension:
        ext = extension if extension.startswith(".") else f".{extension}"
        qs = qs.filter(name__iendswith=ext)
    if path_prefix:
        qs = qs.filter(path__startswith=path_prefix.lstrip("/"))

    compiled: re.Pattern[str] | None = None
    if path_regex:
        try:
            compiled = re.compile(path_regex)
        except re.error as exc:
            raise ValueError(f"Invalid path_regex: {exc}") from exc

    # Glob/regex need full relative paths; apply in Python after DB filters.
    needs_python = bool(name_glob or path_glob or compiled)
    if not needs_python:
        return list(qs)

    matched: list[File] = []
    for f in qs.iterator(chunk_size=500):
        rel = f"{f.path}/{f.name}".lstrip("/") if f.path else (f.name or "")
        if name_glob and not fnmatch.fnmatch(f.name or "", name_glob):
            continue
        if path_glob and not fnmatch.fnmatch(rel, path_glob):
            continue
        if compiled and not compiled.search(rel):
            continue
        matched.append(f)
    return matched


@server.tool(
    name="laxy_list_job_files",
    description=(
        "List job file metadata only (id, path, name, size, type_tags, "
        "download_path, availability). Does not mint download tokens. "
        "For downloads call laxy_get_download_urls. Paginate with page "
        "(1-based) and page_size (max 200). Filters: extension, path_prefix, "
        "name_glob, path_glob, path_regex. which: input|output|both. "
        "Includes job_url."
    ),
    annotations=READ_ONLY,
)
def laxy_list_job_files(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
    which: Annotated[
        str, Field(description="Which filesets: input | output | both")
    ] = "both",
    extension: Annotated[
        str | None,
        Field(description="Filter by extension, e.g. '.tsv' or 'tsv'"),
    ] = None,
    path_prefix: Annotated[
        str | None,
        Field(description="Only files whose path starts with this prefix"),
    ] = None,
    name_glob: Annotated[
        str | None,
        Field(description="fnmatch pattern against the filename only"),
    ] = None,
    path_glob: Annotated[
        str | None,
        Field(description="fnmatch pattern against path/name"),
    ] = None,
    path_regex: Annotated[
        str | None,
        Field(description="Regex matched against path/name"),
    ] = None,
    page: Annotated[
        int, Field(description="1-based page number", ge=1)
    ] = 1,
    page_size: Annotated[
        int, Field(description="Results per page (max 200)", ge=1, le=200)
    ] = 50,
) -> dict[str, Any]:
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    which = (which or "both").lower()
    files: list[File] = []
    filter_kwargs = dict(
        extension=extension,
        path_prefix=path_prefix,
        name_glob=name_glob,
        path_glob=path_glob,
        path_regex=path_regex,
    )
    if which in ("input", "both") and job.input_files_id:
        files.extend(_filter_file_queryset(job.input_files.get_files(), **filter_kwargs))
    if which in ("output", "both") and job.output_files_id:
        files.extend(
            _filter_file_queryset(job.output_files.get_files(), **filter_kwargs)
        )

    page_data = _paginate(files, page, page_size)
    page_files: list[File] = page_data["results"]
    archive_ids = _archive_compute_ids()
    page_data["results"] = [_file_metadata(f, archive_ids) for f in page_files]
    page_data["which"] = which
    page_data["job_id"] = job.id
    page_data["job_url"] = _job_ui_url(job.id, ctx)
    page_data["filters"] = {
        "extension": extension,
        "path_prefix": path_prefix,
        "name_glob": name_glob,
        "path_glob": path_glob,
        "path_regex": path_regex,
    }
    return page_data


def _resolve_job_file(job: Job, file_path: str) -> File:
    path = file_path.lstrip("/")
    fobj: File | None = None
    if path.startswith("input/") and job.input_files_id:
        fobj = job.input_files.get_file_by_path(path[len("input/") :])
        if fobj is None:
            fobj = job.input_files.get_file_by_path(path)
    elif path.startswith("output/") and job.output_files_id:
        fobj = job.output_files.get_file_by_path(path[len("output/") :])
        if fobj is None:
            fobj = job.output_files.get_file_by_path(path)
    else:
        if job.output_files_id:
            fobj = job.output_files.get_file_by_path(path)
        if fobj is None and job.input_files_id:
            fobj = job.input_files.get_file_by_path(path)

    if fobj is None:
        basename = os.path.basename(path)
        for fileset in (
            job.output_files if job.output_files_id else None,
            job.input_files if job.input_files_id else None,
        ):
            if fileset is None:
                continue
            fobj = fileset.get_files().filter(name=basename).first()
            if fobj is not None:
                break

    if fobj is None:
        raise LookupError(f"File not found on job {job.id}: {file_path}")
    return fobj


def _file_text_window(
    fobj: File, max_bytes: int, *, from_end: bool
) -> tuple[str, bool, int]:
    fh = fobj.file
    if fh is None:
        raise LookupError("File data is unavailable (missing location)")
    truncated = False
    raw: bytes | str
    if from_end:
        try:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            start = max(0, size - max_bytes)
            fh.seek(start)
            raw = fh.read(max_bytes)
            truncated = start > 0
        except (OSError, AttributeError, io.UnsupportedOperation):
            raw = fh.read(max_bytes + 1)
            truncated = len(raw) > max_bytes
            raw = raw[:max_bytes]
    else:
        raw = fh.read(max_bytes + 1)
        truncated = len(raw) > max_bytes
        raw = raw[:max_bytes]
    if isinstance(raw, str):
        text = raw
        nbytes = len(raw.encode("utf-8", errors="replace"))
    else:
        raw_bytes = bytes(raw)
        nbytes = len(raw_bytes)
        text = raw_bytes.decode("utf-8", errors="replace")
    return text, truncated, nbytes


def _apply_text_filters(
    text: str, *, tail_lines: int | None, grep: str | None
) -> tuple[str, int | None]:
    lines = text.splitlines()
    match_count = None
    if grep:
        try:
            pattern = re.compile(grep)
        except re.error as exc:
            raise ValueError(f"Invalid grep regex: {exc}") from exc
        lines = [line for line in lines if pattern.search(line)]
        match_count = len(lines)
    if tail_lines is not None:
        lines = lines[-max(1, int(tail_lines)) :]
    return "\n".join(lines), match_count


def _find_named_output(job: Job, filename: str) -> File | None:
    if not job.output_files_id:
        return None
    for fobj in job.output_files.get_files():
        if fobj.name == filename:
            return fobj
    return None


def _main_log_file(job: Job) -> File | None:
    for candidate in ("output/run_job.out", "run_job.out"):
        try:
            return _resolve_job_file(job, candidate)
        except LookupError:
            continue
    return _find_named_output(job, "run_job.out")


def _main_log_tail(job: Job, tail_lines: int = 50, max_bytes: int = 65536) -> dict[str, Any]:
    fobj = _main_log_file(job)
    if fobj is None:
        return {
            "path": "output/run_job.out",
            "content": None,
            "error": "Main log output/run_job.out was not found on this job.",
        }
    try:
        text, truncated, nbytes = _file_text_window(
            fobj, max_bytes, from_end=True
        )
        content, _ = _apply_text_filters(text, tail_lines=tail_lines, grep=None)
    except LookupError as exc:
        return {"path": "output/run_job.out", "content": None, "error": str(exc)}
    return {
        "path": "output/run_job.out",
        "file_id": fobj.id,
        "content": content,
        "tail_lines": tail_lines,
        "bytes_returned": nbytes,
        "truncated": truncated,
    }


def _counts_file(job: Job) -> File:
    if not job.output_files_id:
        raise LookupError(f"Job {job.id} has no output files")
    ranked: list[tuple[int, File]] = []
    for fobj in job.output_files.get_files():
        name = (fobj.name or "").lower()
        rel = f"{fobj.path or ''}/{name}".lower()
        if "featurecount" in name or "featurecount" in rel:
            ranked.append((0, fobj))
        elif name.endswith("counts.tsv") or "gene_count" in name:
            ranked.append((1, fobj))
    if not ranked:
        raise LookupError(
            f"No featureCounts/counts file on job {job.id}. Pass file_id."
        )
    ranked.sort(key=lambda item: (item[0], len(item[1].name or "")))
    return ranked[0][1]


@server.tool(
    name="laxy_read_job_file",
    description=(
        "Read one job file by relative path (e.g. 'output/run_job.out'). "
        "Use tail_lines to return only the last N lines, and grep for a regex "
        "filter, instead of inlining a whole file. Downloads are a separate "
        "call: laxy_get_download_urls. Content is inlined when tail_lines or "
        "grep is set, when include_content=true, or automatically when size "
        "<= 256 KiB. Includes job_url."
    ),
    annotations=READ_ONLY,
)
def laxy_read_job_file(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
    file_path: Annotated[
        str,
        Field(description="Relative path, e.g. output/run_job.out"),
    ],
    max_bytes: Annotated[
        int,
        Field(description="Max bytes to read from the file (tail reads from the end)", ge=1),
    ] = 65536,
    include_content: Annotated[
        bool | None,
        Field(
            description=(
                "Force inline content (true) or metadata only (false). "
                "Default: inline when size <= 256 KiB, or when tail_lines/grep is set."
            )
        ),
    ] = None,
    tail_lines: Annotated[
        int | None,
        Field(description="Return only the last N lines of the read window", ge=1, le=2000),
    ] = None,
    grep: Annotated[
        str | None,
        Field(description="Regex; only matching lines are returned"),
    ] = None,
) -> dict[str, Any]:
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    max_bytes = max(1, min(int(max_bytes), 512 * 1024))
    fobj = _resolve_job_file(job, file_path)
    result = _file_metadata(fobj)
    result["job_id"] = job.id
    result["job_url"] = _job_ui_url(job.id, ctx)
    result["content"] = None
    result["bytes_returned"] = 0
    result["truncated"] = False
    result["max_bytes"] = max_bytes
    result["content_mode"] = "metadata"
    result["message"] = (
        "No download_url in this response. Call laxy_get_download_urls "
        f"with file_ids=['{fobj.id}'] or paths=['{file_path}']."
    )

    size = result.get("size")
    try:
        size_int = int(size) if size is not None else None
    except (TypeError, ValueError):
        size_int = None

    want_slice = tail_lines is not None or bool(grep)
    if include_content is None:
        do_inline = want_slice or (
            size_int is not None and size_int <= _INLINE_SIZE_LIMIT
        )
    else:
        do_inline = bool(include_content) or want_slice

    if not do_inline:
        reason = (
            f"File too large to inline via MCP (size={size_int} bytes; "
            f"limit={_INLINE_SIZE_LIMIT}). Pass tail_lines to read the end."
            if size_int is not None and size_int > _INLINE_SIZE_LIMIT
            else "Size unknown or auto-inline skipped. Pass tail_lines or include_content=true."
        )
        result["message"] = (
            f"{reason} Call laxy_get_download_urls with file_ids=['{fobj.id}']."
        )
        return result

    try:
        text, truncated, nbytes = _file_text_window(
            fobj, max_bytes, from_end=tail_lines is not None
        )
    except LookupError as exc:
        result["error"] = str(exc)
        return result
    content, match_count = _apply_text_filters(
        text, tail_lines=tail_lines, grep=grep
    )
    result["content"] = content
    result["bytes_returned"] = nbytes
    result["truncated"] = truncated
    result["content_mode"] = "tail" if tail_lines else ("grep" if grep else "inline")
    result["tail_lines"] = tail_lines
    result["grep"] = grep
    result["grep_matches"] = match_count
    return result


@server.tool(
    name="laxy_diagnose_job",
    description=(
        "Diagnose a job in one call: status, job_url, the latest event logs, "
        "and the tail of output/run_job.out. Use this before laxy_read_job_file "
        "when the log path is not known."
    ),
    annotations=READ_ONLY,
)
def laxy_diagnose_job(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
    tail_lines: Annotated[
        int, Field(description="Lines of output/run_job.out to return", ge=1, le=500)
    ] = 50,
    event_page_size: Annotated[
        int, Field(description="How many latest events to include", ge=1, le=200)
    ] = 20,
) -> dict[str, Any]:
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    summary = _job_summary(job, ctx)
    summary["params"] = job.params or {}
    summary["exit_code"] = job.exit_code
    events = (
        EventLog.objects.filter(object_id=job.id)
        .order_by("-timestamp")[: max(1, int(event_page_size))]
    )
    summary["events"] = [_event_row(event) for event in events]
    summary["log"] = _main_log_tail(job, tail_lines=tail_lines)
    return summary


@server.tool(
    name="laxy_list_compute_resources",
    description=(
        "Admin only (Django is_staff, same as GET /api/v1/compute-resource/). "
        "Listed only when the MCP token belongs to a staff user. "
        "Same fields as that list, including queue_type. "
        "Does not include the extra JSON blob (SSH private keys). "
        "Paginate with page and page_size."
    ),
    annotations=READ_ONLY,
)
def laxy_list_compute_resources(
    ctx: Context,
    page: Annotated[int, Field(description="1-based page number", ge=1)] = 1,
    page_size: Annotated[
        int, Field(description="Results per page (max 200)", ge=1, le=200)
    ] = 50,
) -> dict[str, Any]:
    user = _current_user(ctx)
    if not _is_rest_admin(user):
        raise PermissionError(
            "Admin only. This tool requires a staff user, "
            "the same check as the REST compute-resource API."
        )
    qs = ComputeResource.objects.all().order_by("-priority", "name")
    page_data = _paginate_queryset(qs, page, page_size)
    page_data["results"] = [
        dict(row)
        for row in ComputeResourceListSerializer(
            page_data["results"], many=True
        ).data
    ]
    return page_data


@server.tool(
    name="laxy_list_pipelines",
    description=(
        "List pipelines available to the authenticated user. Each row includes "
        "versions, default_version, short_description, params_schema and "
        "param_defaults from pipeline metadata (null when unset). Use versions "
        "as pipeline_version for laxy_submit_job. Paginate with page and page_size."
    ),
    annotations=READ_ONLY,
)
def laxy_list_pipelines(
    ctx: Context,
    page: Annotated[int, Field(description="1-based page number", ge=1)] = 1,
    page_size: Annotated[
        int, Field(description="Results per page (max 200)", ge=1, le=200)
    ] = 50,
) -> dict[str, Any]:
    user = _current_user(ctx)
    viewable = get_objects_for_user(user, ["laxy_backend.view_pipeline"])
    qs = (
        Pipeline.objects.filter(Q(owner=user) | Q(public=True))
        .union(viewable)
        .order_by("-created_time")
    )
    page_data = _paginate(list(qs), page, page_size)
    page_data["results"] = [_pipeline_public_row(p) for p in page_data["results"]]
    return page_data


@server.tool(
    name="laxy_list_reference_genomes",
    description=(
        "List reference genomes for laxy_submit_job reference_genome_id. "
        "search matches id, organism/species (the id prefix) or other text fields. "
        "Paginate with page and page_size."
    ),
    annotations=READ_ONLY,
)
def laxy_list_reference_genomes(
    ctx: Context,
    search: Annotated[
        str | None,
        Field(description="Match genome id, species/organism, or other text fields"),
    ] = None,
    page: Annotated[int, Field(description="1-based page number", ge=1)] = 1,
    page_size: Annotated[
        int, Field(description="Results per page (max 200)", ge=1, le=200)
    ] = 50,
) -> dict[str, Any]:
    _current_user(ctx)
    rows: list[dict[str, Any]] = []
    for genome in reference_genomes_for_api():
        if hasattr(genome, "items"):
            rows.append(dict(genome))
        elif hasattr(genome, "__dict__"):
            rows.append(
                {k: v for k, v in vars(genome).items() if not k.startswith("_")}
            )
        elif isinstance(genome, dict):
            rows.append(genome)
    term = (search or "").strip().lower()
    if term:
        def _matches(row: dict[str, Any]) -> bool:
            genome_id = str(row.get("id") or "")
            species = genome_id.split("/", 1)[0].replace("_", " ")
            blob = " ".join(
                str(value)
                for value in row.values()
                if not isinstance(value, (dict, list))
            )
            haystack = f"{genome_id} {species} {blob}".lower()
            return term in haystack

        rows = [row for row in rows if _matches(row)]
    return _paginate(rows, page, page_size)


def _call_api_view(
    view_cls,
    user,
    method: str,
    path: str,
    data: dict | None = None,
    **view_kwargs,
):
    factory = APIRequestFactory()
    method_l = method.lower()
    requester = getattr(factory, method_l)
    if method_l in ("get", "delete", "head"):
        request = requester(path)
    else:
        request = requester(path, data or {}, format="json")
    force_authenticate(request, user=user)
    response = view_cls.as_view()(request, **view_kwargs)
    if hasattr(response, "render"):
        response.render()
    raw = getattr(response, "content", b"") or b""
    if isinstance(raw, str):
        text = raw
    else:
        text = bytes(raw).decode("utf-8", errors="replace")
    try:
        body = json.loads(text or "{}")
    except json.JSONDecodeError:
        data = getattr(response, "data", None)
        body = data if isinstance(data, dict) else {"raw": text[:500]}
    if not isinstance(body, dict):
        body = {"raw": body}
    return response.status_code, body


def _write_tools_enabled() -> bool:
    return bool(getattr(settings, "MCP_ENABLE_WRITE_TOOLS", False))


def _create_job_from_pipelinerun(
    user, pipelinerun_id: str, job_body: dict[str, Any] | None = None
) -> dict[str, Any]:
    factory = APIRequestFactory()
    request = factory.post(
        f"/api/v1/job/?pipeline_run_id={pipelinerun_id}",
        job_body or {},
        format="json",
    )
    force_authenticate(request, user=user)
    response = JobCreate.as_view()(request)
    if hasattr(response, "render"):
        response.render()
    try:
        job = json.loads(response.content.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        job = {}
    if response.status_code >= 400 or not job.get("id"):
        raise RuntimeError(
            f"job create failed ({response.status_code}): "
            f"{response.content.decode('utf-8', errors='replace')[:500]}"
        )
    return job


@server.tool(
    name="laxy_get_pipeline_run",
    description=(
        "Get a PipelineRun by id (pipeline name, params, sample_cart id). "
        "Use after laxy_clone_job to inspect params before laxy_start_job."
    ),
    annotations=READ_ONLY,
)
def laxy_get_pipeline_run(ctx: Context, pipeline_run_id: str) -> dict[str, Any]:
    user = _current_user(ctx)
    _pipelinerun_for_user(user, pipeline_run_id)
    status_code, body = _call_api_view(
        PipelineRunView,
        user,
        "get",
        f"/api/v1/pipelinerun/{pipeline_run_id}/",
        uuid=pipeline_run_id,
    )
    if status_code >= 400:
        raise RuntimeError(f"pipeline run get failed ({status_code}): {body}")
    return body


@server.tool(
    name="laxy_get_sample_cart",
    description=(
        "Get a SampleCart by id (samples and file URLs). "
        "Use after laxy_clone_job to inspect inputs before laxy_start_job."
    ),
    annotations=READ_ONLY,
)
def laxy_get_sample_cart(ctx: Context, sample_cart_id: str) -> dict[str, Any]:
    user = _current_user(ctx)
    _samplecart_for_user(user, sample_cart_id)
    status_code, body = _call_api_view(
        SampleCartView,
        user,
        "get",
        f"/api/v1/samplecart/{sample_cart_id}/",
        uuid=sample_cart_id,
    )
    if status_code >= 400:
        raise RuntimeError(f"sample cart get failed ({status_code}): {body}")
    return body


@server.tool(
    name="laxy_update_pipeline_run",
    description=(
        "Update a PipelineRun (PATCH). Pass fields to change, e.g. params "
        "(genome, pipeline_version, description, pipeline-specific options) "
        "and/or description. Call after laxy_clone_job and before laxy_start_job. "
        "Requires LAXY_MCP_ENABLE_WRITE_TOOLS=yes."
    ),
    annotations=WRITE,
)
def laxy_update_pipeline_run(
    ctx: Context,
    pipeline_run_id: str,
    params: dict[str, Any] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )
    user = _current_user(ctx)
    _pipelinerun_for_user(user, pipeline_run_id)
    payload: dict[str, Any] = {}
    if params is not None:
        payload["params"] = params
    if description is not None:
        payload["description"] = description
    if not payload:
        raise ValueError("Provide at least one of params or description to update.")
    status_code, body = _call_api_view(
        PipelineRunView,
        user,
        "patch",
        f"/api/v1/pipelinerun/{pipeline_run_id}/",
        payload,
        uuid=pipeline_run_id,
    )
    if status_code >= 400:
        raise RuntimeError(f"pipeline run update failed ({status_code}): {body}")
    # PATCH returns 204 with an empty body; return the updated representation.
    status_code, body = _call_api_view(
        PipelineRunView,
        user,
        "get",
        f"/api/v1/pipelinerun/{pipeline_run_id}/",
        uuid=pipeline_run_id,
    )
    if status_code >= 400:
        raise RuntimeError(
            f"pipeline run updated but re-fetch failed ({status_code}): {body}"
        )
    return body


@server.tool(
    name="laxy_update_sample_cart",
    description=(
        "Replace SampleCart contents (PUT). samples is a list of "
        "{name, files: [{R1, R2?}]} (one object per lane; R1 and R2 together). "
        "A list of single-key dicts [{R1},{R2}] is merged into that shape. "
        "Call after laxy_clone_job and before laxy_start_job. "
        "Requires LAXY_MCP_ENABLE_WRITE_TOOLS=yes."
    ),
    annotations=WRITE,
)
def laxy_update_sample_cart(
    ctx: Context,
    sample_cart_id: str,
    samples: list[SampleSpec],
    name: str | None = None,
) -> dict[str, Any]:
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )
    user = _current_user(ctx)
    _samplecart_for_user(user, sample_cart_id)
    payload: dict[str, Any] = {"samples": _normalize_samples(samples)}
    if name is not None:
        payload["name"] = name
    status_code, body = _call_api_view(
        SampleCartView,
        user,
        "put",
        f"/api/v1/samplecart/{sample_cart_id}/",
        payload,
        uuid=sample_cart_id,
    )
    if status_code >= 400:
        raise RuntimeError(f"sample cart update failed ({status_code}): {body}")
    return body


@server.tool(
    name="laxy_submit_job",
    description=(
        "Submit a brand-new Laxy job in one step: creates a sample cart, "
        "pipeline run, then job. samples is [{name, files: [{R1, R2?}]}]; "
        "R1 and R2 belong on the same lane object. Call laxy_list_pipelines "
        "for valid pipeline_version values and params_schema. "
        "pipeline_params is merged into the pipeline params object. "
        "dry_run=true validates and returns the payload without creating "
        "anything (no write-tool gate). Otherwise requires "
        "LAXY_MCP_ENABLE_WRITE_TOOLS=yes. Returns job_url."
    ),
    annotations=DESTRUCTIVE,
)
def laxy_submit_job(
    ctx: Context,
    pipeline_name: Annotated[str, Field(description="Pipeline name from laxy_list_pipelines")],
    pipeline_version: Annotated[
        str, Field(description="One of that pipeline's versions")
    ],
    samples: list[SampleSpec],
    description: str = "",
    reference_genome_id: str | None = None,
    genome_fasta_url: str | None = None,
    genome_annotation_url: str | None = None,
    pipeline_params: Annotated[
        dict[str, Any] | None,
        Field(
            description=(
                "Pipeline-specific options merged into params. Shape depends on "
                "the pipeline; see laxy_list_pipelines params_schema / param_defaults."
            )
        ),
    ] = None,
    compute_resource_id: str | None = None,
    dry_run: Annotated[
        bool,
        Field(description="Validate only; do not create a cart, run, or job"),
    ] = False,
) -> dict[str, Any]:
    user = _current_user(ctx)
    errors: list[str] = []
    try:
        normalised = _normalize_samples(samples)
    except ValueError as exc:
        normalised = []
        errors.append(str(exc))

    pipeline = Pipeline.objects.filter(name=pipeline_name).first()
    versions: list[Any] = []
    if pipeline is None:
        errors.append(f"Unknown pipeline: {pipeline_name}")
    else:
        versions = list((pipeline.metadata or {}).get("versions") or [])
        if versions and pipeline_version not in versions:
            errors.append(
                f"pipeline_version {pipeline_version!r} is not in {versions}"
            )

    if bool(genome_fasta_url) ^ bool(genome_annotation_url):
        errors.append("genome_fasta_url and genome_annotation_url must be set together")
    if reference_genome_id and not (genome_fasta_url and genome_annotation_url):
        known = {row.get("id") for row in reference_genomes_for_api()}
        if reference_genome_id not in known:
            errors.append(f"Unknown reference_genome_id: {reference_genome_id}")
    if compute_resource_id and not ComputeResource.objects.filter(
        id=compute_resource_id
    ).exists():
        errors.append(f"Unknown compute_resource_id: {compute_resource_id}")

    params: dict[str, Any] = {
        "pipeline_version": pipeline_version,
        "description": description,
    }
    if genome_fasta_url and genome_annotation_url:
        params["genome"] = None
        params["user_genome"] = {
            "fasta_url": genome_fasta_url.strip(),
            "annotation_url": genome_annotation_url.strip(),
        }
    elif reference_genome_id:
        params["genome"] = reference_genome_id
    if pipeline_params:
        params.update(pipeline_params)

    preview = {
        "dry_run": True,
        "valid": not errors,
        "errors": errors,
        "pipeline": pipeline_name,
        "pipeline_version": pipeline_version,
        "allowed_versions": versions,
        "samples": normalised,
        "params": params,
        "compute_resource_id": compute_resource_id,
    }
    if dry_run:
        return preview
    if errors:
        raise ValueError("; ".join(errors))
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )

    status_code, samplecart = _call_api_view(
        SampleCartCreate, user, "post", "/api/v1/samplecart/", {"samples": normalised}
    )
    if status_code >= 400 or not samplecart.get("id"):
        raise RuntimeError(f"samplecart create failed ({status_code}): {samplecart}")

    pipelinerun_payload = {
        "pipeline": pipeline_name,
        "sample_cart": samplecart["id"],
        "params": params,
        "description": description,
    }
    status_code, pipelinerun = _call_api_view(
        PipelineRunCreate, user, "post", "/api/v1/pipelinerun/", pipelinerun_payload
    )
    if status_code >= 400 or not pipelinerun.get("id"):
        raise RuntimeError(f"pipelinerun create failed ({status_code}): {pipelinerun}")

    job_body: dict[str, Any] = {}
    if compute_resource_id:
        job_body["compute_resource"] = compute_resource_id

    job = _create_job_from_pipelinerun(user, pipelinerun["id"], job_body)
    return _attach_job_url(
        {
            "job_id": job["id"],
            "samplecart_id": samplecart["id"],
            "pipelinerun_id": pipelinerun["id"],
            "status": job.get("status"),
            "dry_run": False,
        },
        job["id"],
        ctx,
    )


@server.tool(
    name="laxy_clone_job",
    description=(
        "Copy an existing job's SampleCart and PipelineRun. Does not create a "
        "Job unless start=true. Optional params replaces pipeline-run params; "
        "optional samples replaces the cloned cart; optional description is "
        "patched onto the pipeline run. start=true then calls laxy_start_job. "
        "Requires LAXY_MCP_ENABLE_WRITE_TOOLS=yes. Includes job_url of the "
        "source job, and of the new job when started. "
        "dry_run=true validates samples and reports whether a job would be "
        "queued, without creating a cart, pipeline run, or job."
    ),
    annotations=WRITE,
)
def laxy_clone_job(
    ctx: Context,
    job_id: str,
    params: Annotated[
        dict[str, Any] | None,
        Field(description="If set, PATCH these params onto the cloned pipeline run"),
    ] = None,
    samples: Annotated[
        list[SampleSpec] | None,
        Field(description="If set, replace the cloned sample cart with these samples"),
    ] = None,
    description: str | None = None,
    start: Annotated[
        bool,
        Field(description="If true, create and queue a Job from the clone"),
    ] = False,
    compute_resource_id: str | None = None,
    dry_run: Annotated[
        bool,
        Field(
            description=(
                "Validate only. Does not clone or, when start=true, queue a job."
            )
        ),
    ] = False,
) -> dict[str, Any]:
    user = _current_user(ctx)
    _job_for_user(user, job_id)
    errors: list[str] = []
    if samples is not None:
        try:
            _normalize_samples(samples)
        except ValueError as exc:
            errors.append(str(exc))
    if dry_run:
        return {
            "dry_run": True,
            "valid": not errors,
            "errors": errors,
            "cloned_from": job_id,
            "job_url": _job_ui_url(job_id, ctx),
            "would_start": bool(start),
            "note": "No SampleCart, PipelineRun, or Job was created.",
        }
    if errors:
        raise ValueError("; ".join(errors))
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )

    status_code, body = _call_api_view(
        JobClone,
        user,
        "post",
        f"/api/v1/job/{job_id}/clone/",
        {},
        job_id=job_id,
    )
    if not isinstance(body, dict):
        body = {}
    if not (200 <= status_code < 300):
        raise RuntimeError(f"clone failed ({status_code}): {body}")
    pipelinerun_id = body.get("pipelinerun_id")
    samplecart_id = body.get("samplecart_id")
    result: dict[str, Any] = {
        "cloned_from": job_id,
        "job_url": _job_ui_url(job_id, ctx),
        "pipelinerun_id": pipelinerun_id,
        "samplecart_id": samplecart_id,
        "pipeline": body.get("pipeline"),
        "started": False,
        "next_step": (
            "This clone is not a Job yet. Edit it or start it with these tools: "
            f"laxy_get_pipeline_run(pipeline_run_id={pipelinerun_id!r}); "
            f"laxy_get_sample_cart(sample_cart_id={samplecart_id!r}); "
            f"laxy_update_pipeline_run(pipeline_run_id={pipelinerun_id!r}, params={{...}}); "
            f"laxy_update_sample_cart(sample_cart_id={samplecart_id!r}, samples=[...]); "
            f"laxy_start_job(pipeline_run_id={pipelinerun_id!r}). "
            "Or call laxy_clone_job again with start=true and optional params/samples."
        ),
    }
    if samples is not None and samplecart_id:
        updated_cart = laxy_update_sample_cart(
            ctx, samplecart_id, samples, name=None
        )
        result["sample_cart_updated"] = True
        result["samplecart"] = updated_cart
    if (params is not None or description is not None) and pipelinerun_id:
        updated_run = laxy_update_pipeline_run(
            ctx, pipelinerun_id, params=params, description=description
        )
        result["pipeline_run_updated"] = True
        result["pipelinerun"] = updated_run
    if start and pipelinerun_id:
        started = laxy_start_job(
            ctx, pipelinerun_id, compute_resource_id=compute_resource_id
        )
        result["started"] = True
        result["job_id"] = started.get("job_id")
        result["status"] = started.get("status")
        result["job_url"] = started.get("job_url")
        result["next_step"] = (
            f"Job {result['job_id']} was queued. Open {result['job_url']}."
        )
    return result


@server.tool(
    name="laxy_start_job",
    description=(
        "Create and start a Job from an existing PipelineRun "
        "(e.g. after laxy_clone_job). dry_run=true checks the run has a "
        "pipeline and samples and does not queue a job. Otherwise requires "
        "LAXY_MCP_ENABLE_WRITE_TOOLS=yes. Returns job_url."
    ),
    annotations=DESTRUCTIVE,
)
def laxy_start_job(
    ctx: Context,
    pipeline_run_id: str,
    compute_resource_id: str | None = None,
    dry_run: Annotated[
        bool,
        Field(description="Validate the pipeline run without creating a job"),
    ] = False,
) -> dict[str, Any]:
    user = _current_user(ctx)
    run = _pipelinerun_for_user(user, pipeline_run_id)
    errors: list[str] = []
    if not getattr(run, "pipeline", None):
        errors.append("Pipeline run has no pipeline")
    cart = getattr(run, "sample_cart", None)
    samples = getattr(cart, "samples", None) if cart is not None else None
    if not samples:
        errors.append("Pipeline run sample cart has no samples")
    if compute_resource_id and not ComputeResource.objects.filter(
        id=compute_resource_id
    ).exists():
        errors.append(f"Unknown compute_resource_id: {compute_resource_id}")
    if dry_run:
        return {
            "dry_run": True,
            "valid": not errors,
            "errors": errors,
            "pipelinerun_id": pipeline_run_id,
            "samplecart_id": getattr(cart, "id", None),
            "sample_count": len(samples) if isinstance(samples, list) else 0,
        }
    if errors:
        raise ValueError("; ".join(errors))
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )

    job_body: dict[str, Any] = {}
    if compute_resource_id:
        job_body["compute_resource"] = compute_resource_id

    job = _create_job_from_pipelinerun(user, pipeline_run_id, job_body)
    return _attach_job_url(
        {
            "job_id": job["id"],
            "status": job.get("status"),
            "pipelinerun_id": pipeline_run_id,
            "samplecart_id": getattr(cart, "id", None),
            "dry_run": False,
        },
        job["id"],
        ctx,
    )


@server.tool(
    name="laxy_cancel_job",
    description=(
        "Mark a running or queued job cancelled (PATCH status=cancelled) and "
        "request a remote kill. This does not confirm the pipeline process "
        "has stopped. Already-cancelled jobs stay cancelled. "
        "Requires LAXY_MCP_ENABLE_WRITE_TOOLS=yes."
    ),
    annotations=DESTRUCTIVE,
)
def laxy_cancel_job(ctx: Context, job_id: str) -> dict[str, Any]:
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    if job.status in (Job.STATUS_COMPLETE, Job.STATUS_FAILED):
        raise ValueError(
            f"Job {job_id} is already {job.status} and cannot be cancelled."
        )
    if job.status == Job.STATUS_CANCELLED:
        return _attach_job_url(
            {
                "job_id": job.id,
                "status": job.status,
                "already_cancelled": True,
            },
            job.id,
            ctx,
        )

    status_code, body = _call_api_view(
        JobView,
        user,
        "patch",
        f"/api/v1/job/{job_id}/",
        {"status": Job.STATUS_CANCELLED},
        uuid=job_id,
    )
    if status_code >= 400:
        raise RuntimeError(f"cancel failed ({status_code}): {body}")

    job.refresh_from_db()
    return _attach_job_url(
        {
            "job_id": job.id,
            "status": job.status,
            "already_cancelled": False,
            "remote_kill": "requested",
            "note": (
                "Job status is cancelled and a remote kill was requested. "
                "This does not confirm the pipeline process has stopped."
            ),
        },
        job.id,
        ctx,
    )


def _job_access_token(job_id: str) -> AccessToken | None:
    """UI share token for a job (excludes MCP ``mcpdl.*`` download tokens)."""
    ct = _job_access_token_ct()
    return (
        AccessToken.objects.filter(object_id=job_id, content_type=ct)
        .exclude(token__startswith=ACCESS_TOKEN_MCP_DOWNLOAD_PREFIX)
        .order_by("created_time")
        .first()
    )


@server.tool(
    name="laxy_get_job_share",
    description=(
        "Read the current UI job share link (token, expiry, share_url, job_url). "
        "Does not create or change a token. Use laxy_share_job to mint or update one."
    ),
    annotations=READ_ONLY,
)
def laxy_get_job_share(ctx: Context, job_id: str) -> dict[str, Any]:
    user = _current_user(ctx)
    _job_for_user(user, job_id)
    payload = _job_share_payload(_job_access_token(job_id), job_id, ctx)
    payload["job_url"] = _job_ui_url(job_id, ctx)
    return payload


@server.tool(
    name="laxy_share_job",
    description=(
        "Mint or update the UI job share link. expires_in_seconds defaults to "
        "7 days. Non-expiring links are not created. To read the current link "
        "without writing, use laxy_get_job_share. Requires "
        "LAXY_MCP_ENABLE_WRITE_TOOLS=yes."
    ),
    annotations=WRITE,
)
def laxy_share_job(
    ctx: Context,
    job_id: str,
    expires_in_seconds: Annotated[
        int | None,
        Field(description="TTL from now. Default 7 days."),
    ] = None,
) -> dict[str, Any]:
    user = _current_user(ctx)
    _job_for_user(user, job_id)
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )
    secs = 7 * 24 * 60 * 60 if expires_in_seconds is None else int(expires_in_seconds)
    secs = max(60, secs)
    expiry_time = (timezone.now() + timedelta(seconds=secs)).isoformat()
    status_code, body = _call_api_view(
        JobAccessTokenView,
        user,
        "put",
        f"/api/v1/job/{job_id}/accesstoken/",
        {"expiry_time": expiry_time},
        job_id=job_id,
    )
    if status_code >= 400:
        raise RuntimeError(f"share job failed ({status_code}): {body}")
    token_obj = _job_access_token(job_id)
    payload = _job_share_payload(token_obj, job_id, ctx)
    payload["job_url"] = _job_ui_url(job_id, ctx)
    payload["created_or_updated"] = True
    return payload


@server.tool(
    name="laxy_revoke_job_share",
    description=(
        "Revoke the UI job sharing access_token only. Does not delete mcpdl.* "
        "download tokens; use laxy_revoke_download_tokens for those. "
        "Requires LAXY_MCP_ENABLE_WRITE_TOOLS=yes."
    ),
    annotations=DESTRUCTIVE,
)
def laxy_revoke_job_share(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
) -> dict[str, Any]:
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )
    user = _current_user(ctx)
    _job_for_user(user, job_id)
    result: dict[str, Any] = {
        "job_id": job_id,
        "job_url": _job_ui_url(job_id, ctx),
        "share_revoked": False,
        "share_token_id": None,
    }
    token_obj = _job_access_token(job_id)
    if token_obj is None:
        result["message"] = "No UI share token exists."
        return result
    status_code, body = _call_api_view(
        AccessTokenView,
        user,
        "delete",
        f"/api/v1/accesstoken/{token_obj.id}/",
        uuid=token_obj.id,
    )
    if status_code >= 400 and status_code != 204:
        raise RuntimeError(f"revoke share failed ({status_code}): {body}")
    result["share_revoked"] = True
    result["share_token_id"] = token_obj.id
    return result


@server.tool(
    name="laxy_revoke_download_tokens",
    description=(
        "Delete this user's short-lived mcpdl.* download tokens for a job. "
        "Does not revoke the UI share link (laxy_revoke_job_share). "
        "Call after downloads finish. Requires LAXY_MCP_ENABLE_WRITE_TOOLS=yes."
    ),
    annotations=DESTRUCTIVE,
)
def laxy_revoke_download_tokens(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
) -> dict[str, Any]:
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )
    user = _current_user(ctx)
    _job_for_user(user, job_id)
    revoked = _revoke_mcp_download_tokens(job_id, user)
    return {
        "job_id": job_id,
        "job_url": _job_ui_url(job_id, ctx),
        "download_tokens_revoked": revoked,
        "download_tokens_revoked_count": len(revoked),
    }


@server.tool(
    name="laxy_get_download_urls",
    description=(
        "Preferred download helper: mint one short-lived job-scoped mcpdl.* "
        "access_token and return download_url(s) for selected job files. "
        "Select via file_ids and/or paths and/or path_glob and/or path_prefix "
        "(at least one required). Independent of UI share tokens. "
        "which: input|output|both. "
        f"expires_in_seconds default {_DEFAULT_DOWNLOAD_TTL_SECONDS} "
        f"(max {_SCHEMA_MAX_DOWNLOAD_TTL_SECONDS}s / "
        "LAXY_MCP_JOB_DOWNLOAD_TOKEN_MAX_HOURS). After downloading, revoke with "
        "laxy_revoke_download_tokens. max_files caps the selection (max 200). "
        "Curl URLs without the MCP bearer token. Includes job_url."
    ),
    annotations=READ_ONLY,
)
def laxy_get_download_urls(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
    file_ids: Annotated[
        list[str] | None,
        Field(description="File IDs from laxy_list_job_files"),
    ] = None,
    paths: Annotated[
        list[str] | None,
        Field(description="Relative paths, e.g. ['output/run_job.out']"),
    ] = None,
    path_glob: Annotated[
        str | None, Field(description="fnmatch on path/name")
    ] = None,
    path_prefix: Annotated[
        str | None, Field(description="Path prefix filter")
    ] = None,
    which: Annotated[
        str, Field(description="input | output | both")
    ] = "both",
    expires_in_seconds: Annotated[
        int,
        Field(
            description=(
                f"Token TTL seconds (default {_DEFAULT_DOWNLOAD_TTL_SECONDS}, "
                f"max {_SCHEMA_MAX_DOWNLOAD_TTL_SECONDS})"
            ),
            ge=60,
            le=_SCHEMA_MAX_DOWNLOAD_TTL_SECONDS,
        ),
    ] = _DEFAULT_DOWNLOAD_TTL_SECONDS,
    max_files: Annotated[
        int, Field(description="Max files to return (max 200)", ge=1, le=200)
    ] = _MAX_DOWNLOAD_URL_FILES,
) -> dict[str, Any]:
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    files = _select_job_files_for_download(
        job,
        which=which,
        file_ids=file_ids,
        paths=paths,
        path_glob=path_glob,
        path_prefix=path_prefix,
        limit=max_files,
    )
    job_token = _mint_job_download_token(
        job, user, expires_in_seconds=expires_in_seconds
    )
    payload = _download_token_payload(
        job_token, ctx, expires_in_seconds=expires_in_seconds
    )
    file_rows = [_file_summary(f, ctx, job_token) for f in files]
    example = None
    if file_rows:
        first = file_rows[0]
        example = f"curl -fL -o '{first['name']}' '{first['download_url']}'"
    return {
        "job_id": job_id,
        "job_url": _job_ui_url(job_id, ctx),
        "count": len(file_rows),
        "files": file_rows,
        "curl_example": example,
        **payload,
    }


@server.tool(
    name="laxy_get_job_tarball_urls",
    description=(
        "Return REST URLs for job input/output/full tar.gz archives using a "
        "short-lived mcpdl.* download token (same mechanism as "
        "laxy_get_download_urls). Does NOT create or use the UI job share "
        "token. which: output (default), input, full, or all. "
        "expires_in_seconds default 3600 (1h). Curl without MCP bearer auth."
    ),
    annotations=READ_ONLY,
)
def laxy_get_job_tarball_urls(
    ctx: Context,
    job_id: Annotated[str, Field(description="Job ID")],
    which: Annotated[
        str,
        Field(description="Archive set: output | input | full | all"),
    ] = "output",
    expires_in_seconds: Annotated[
        int,
        Field(
            description=(
                "mcpdl.* token TTL in seconds "
                f"(default {_DEFAULT_DOWNLOAD_TTL_SECONDS}, "
                f"max {_SCHEMA_MAX_DOWNLOAD_TTL_SECONDS})"
            ),
            ge=60,
            le=_SCHEMA_MAX_DOWNLOAD_TTL_SECONDS,
        ),
    ] = _DEFAULT_DOWNLOAD_TTL_SECONDS,
) -> dict[str, Any]:
    user = _current_user(ctx)
    job = _job_for_user(user, job_id)
    which_l = (which or "output").lower()
    if which_l not in ("input", "output", "full", "all"):
        raise ValueError("which must be one of: input, output, full, all")

    token_obj = _mint_job_download_token(
        job, user, expires_in_seconds=expires_in_seconds
    )

    api = _api_base_url(ctx)
    token_q = urlencode({"access_token": token_obj.token})

    def _url(path: str) -> str:
        return f"{api}{path}?{token_q}" if api else f"{path}?{token_q}"

    urls: dict[str, str] = {}
    if which_l in ("input", "all"):
        urls["input"] = _url(f"/api/v1/job/{job_id}/download/input/")
    if which_l in ("output", "all"):
        urls["output"] = _url(f"/api/v1/job/{job_id}/download/output/")
    if which_l in ("full", "all"):
        urls["full"] = _url(f"/api/v1/job/{job_id}/download/")

    payload = _download_token_payload(
        token_obj, ctx, expires_in_seconds=expires_in_seconds
    )
    return {
        "job_id": job_id,
        "job_url": _job_ui_url(job_id, ctx),
        "urls": urls,
        "curl_example": (
            f"curl -fL -o {job_id}_output.tar.gz "
            f"'{urls.get('output') or next(iter(urls.values()))}'"
            if urls
            else None
        ),
        **payload,
    }


@server.tool(
    name="laxy_ena_query",
    description=(
        "Proxy ENA metadata lookup by accession list (comma-separated). "
        "Returns ENA XML converted to JSON. Pass fields (comma-separated key "
        "names) to keep only those keys and drop the rest of the verbose tree. "
        "For FASTQ URLs ready to submit, use laxy_samples_from_ena."
    ),
    annotations=READ_ONLY,
)
def laxy_ena_query(
    ctx: Context,
    accessions: str,
    fields: Annotated[
        str | None,
        Field(
            description=(
                "Comma-separated key names to keep (case-insensitive). "
                "Omit to return the full ENA document."
            )
        ),
    ] = None,
) -> dict[str, Any]:
    _current_user(ctx)
    acc = accessions.strip()
    if not acc:
        raise ValueError("accessions is required (comma-separated ENA accessions).")
    status_code, body = _call_api_view(
        ENAQueryView,
        _current_user(ctx),
        "get",
        f"/api/v1/ena/?accessions={acc}",
    )
    if status_code >= 400:
        raise RuntimeError(f"ENA query failed ({status_code}): {body}")
    if not isinstance(body, dict):
        body = {"result": body}
    if fields:
        wanted = {part.strip() for part in fields.split(",") if part.strip()}
        pruned = _prune_to_fields(body, wanted)
        return {"fields": sorted(wanted), "result": pruned or {}}
    return body


@server.tool(
    name="laxy_ena_fastq_urls",
    description=(
        "Resolve ENA accessions to run-table rows including FASTQ FTP URLs, "
        "md5, size and read counts. Pass comma-separated accessions "
        "(e.g. 'SRR950078' or 'PRJNA123,SRR1'). To turn those rows into the "
        "samples list laxy_submit_job expects, use laxy_samples_from_ena."
    ),
    annotations=READ_ONLY,
)
def laxy_ena_fastq_urls(ctx: Context, accessions: str) -> dict[str, Any]:
    user = _current_user(ctx)
    acc = accessions.strip()
    if not acc:
        raise ValueError("accessions is required (comma-separated ENA accessions).")
    status_code, body = _call_api_view(
        ENAFastqUrlQueryView,
        user,
        "get",
        f"/api/v1/ena/fastqs/?accessions={acc}",
    )
    if status_code >= 400:
        raise RuntimeError(f"ENA fastq URL query failed ({status_code}): {body}")
    return body if isinstance(body, dict) else {"result": body}


@server.tool(
    name="laxy_samples_from_ena",
    description=(
        "Resolve ENA accessions and return samples in the laxy_submit_job "
        "shape: [{name, files: [{R1, R2?}]}]. Runs that share a sample alias "
        "become extra lanes on one sample. Also returns the raw run table."
    ),
    annotations=READ_ONLY,
)
def laxy_samples_from_ena(ctx: Context, accessions: str) -> dict[str, Any]:
    runs = laxy_ena_fastq_urls(ctx, accessions)
    samples = _samples_from_ena_runs(runs if isinstance(runs, dict) else {})
    return {
        "accessions": accessions,
        "samples": samples,
        "sample_count": len(samples),
        "runs": runs,
    }


@server.tool(
    name="laxy_remote_browse",
    description=(
        "List one level of a remote HTTP(S)/FTP directory (or site plugin "
        "such as Zenodo / Nextcloud public share). Optional fileglob "
        "(default '*') filters filenames. Returns {listing: [...]} with "
        "type/name/location per entry."
    ),
    annotations=READ_ONLY,
)
def laxy_remote_browse(
    ctx: Context,
    url: str,
    fileglob: str = "*",
) -> dict[str, Any]:
    user = _current_user(ctx)
    if not (url or "").strip():
        raise ValueError("url is required.")
    status_code, body = _call_api_view(
        RemoteBrowseView,
        user,
        "post",
        "/api/v1/remote-browse/",
        {"url": url.strip(), "fileglob": fileglob or "*"},
    )
    if status_code >= 400:
        raise RuntimeError(f"remote browse failed ({status_code}): {body}")
    return body if isinstance(body, dict) else {"listing": body}


@server.tool(
    name="laxy_send_to_degust",
    description=(
        "Send a counts matrix to Degust. Pass job_id to auto-select a "
        "featureCounts or *counts.tsv output, or file_id to override. "
        "Returns the session URL plus job_url. "
        "Requires LAXY_MCP_ENABLE_WRITE_TOOLS=yes."
    ),
    annotations=WRITE,
)
def laxy_send_to_degust(
    ctx: Context,
    job_id: Annotated[
        str | None,
        Field(description="Job whose featureCounts output should be uploaded"),
    ] = None,
    file_id: Annotated[
        str | None,
        Field(description="Counts file id. Overrides the auto-detected job file."),
    ] = None,
) -> dict[str, Any]:
    if not _write_tools_enabled():
        raise PermissionError(
            "Write tools are disabled. Set LAXY_MCP_ENABLE_WRITE_TOOLS=yes to enable."
        )
    user = _current_user(ctx)
    if not file_id:
        if not job_id:
            raise ValueError("Provide job_id or file_id")
        job = _job_for_user(user, job_id)
        fobj = _counts_file(job)
        file_id = fobj.id
    else:
        try:
            fobj = File.objects.select_related("owner", "fileset").get(id=file_id)
        except File.DoesNotExist as exc:
            raise LookupError(f"Unknown file ID: {file_id}") from exc
        if not user.is_superuser and fobj.owner_id != user.pk:
            raise PermissionError(f"No access to file {file_id}")
    status_code, body = _call_api_view(
        SendFileToDegust,
        user,
        "post",
        f"/api/v1/action/send-to/degust/{file_id}/",
        file_id=file_id,
    )
    if status_code >= 400:
        raise RuntimeError(f"send to Degust failed ({status_code}): {body}")
    if not isinstance(body, dict):
        body = {"result": body}
    body["file_id"] = file_id
    if job_id:
        body["job_id"] = job_id
        body["job_url"] = _job_ui_url(job_id, ctx)
    return body
