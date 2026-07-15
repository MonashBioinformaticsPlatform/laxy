"""
View-level tests for HTTP Range request support (RFC 7233), covering
FileView/FileContentDownload/JobFileView + StreamFileMixin.

Uses file://-backed Files (a real local temp file, seekable via
FileSystemStorage) rather than a live SFTP host, per the plan's Phase 4
test guidance. A mocked http:// backed File is used for the non-seekable
backend case.
"""

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from laxy_backend import util
from ..models import Job, File, FileSet, ComputeResource, AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


def _create_user_and_login(username="testuser", password="testpass", is_superuser=False):
    user = User.objects.create_user(username, "", password)
    user.is_superuser = is_superuser
    user.save()

    client = APIClient(HTTP_CONTENT_TYPE="application/json")
    client.login(username=username, password=password)
    return user, client


class RangeRequestFileViewTest(TestCase):
    def setUp(self):
        self.user, self.user_client = _create_user_and_login(
            "rangeuser", "rangepass"
        )

        # Easy-to-index content so byte windows are simple to assert on.
        self.content = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.size = len(self.content)

        job_dir = os.path.join(tempfile.gettempdir(), util.generate_uuid())
        os.makedirs(job_dir, exist_ok=True)
        fd, fpath = tempfile.mkstemp(dir=job_dir)
        os.write(fd, self.content)
        os.close(fd)
        self.fpath = fpath

        self.file_obj = File(
            location=f"file://{fpath}",
            name=Path(fpath).name,
            path=Path(fpath).parent,
            owner=self.user,
        )
        self.file_obj.save()

    def tearDown(self):
        self.file_obj.delete()
        self.user.delete()

    def _url(self):
        return reverse("laxy_backend:file", args=[self.file_obj.uuid()])

    def test_no_range_returns_full_200_with_accept_ranges(self):
        response = self.user_client.get(
            self._url(), content_type="application/octet-stream"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["Content-Length"], str(self.size))
        content = b"".join(chunk for chunk in response.streaming_content)
        self.assertEqual(content, self.content)

    def test_range_bytes_0_9_returns_206(self):
        response = self.user_client.get(
            self._url(),
            content_type="application/octet-stream",
            HTTP_RANGE="bytes=0-9",
        )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], f"bytes 0-9/{self.size}")
        self.assertEqual(response["Content-Length"], "10")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        content = b"".join(chunk for chunk in response.streaming_content)
        self.assertEqual(content, self.content[0:10])

    def test_range_open_ended_returns_last_bytes(self):
        start = self.size - 5
        response = self.user_client.get(
            self._url(),
            content_type="application/octet-stream",
            HTTP_RANGE=f"bytes={start}-",
        )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(
            response["Content-Range"], f"bytes {start}-{self.size - 1}/{self.size}"
        )
        self.assertEqual(response["Content-Length"], "5")
        content = b"".join(chunk for chunk in response.streaming_content)
        self.assertEqual(content, self.content[start:])

    def test_range_suffix_returns_last_bytes(self):
        response = self.user_client.get(
            self._url(),
            content_type="application/octet-stream",
            HTTP_RANGE="bytes=-5",
        )

        self.assertEqual(response.status_code, 206)
        start = self.size - 5
        self.assertEqual(
            response["Content-Range"], f"bytes {start}-{self.size - 1}/{self.size}"
        )
        self.assertEqual(response["Content-Length"], "5")
        content = b"".join(chunk for chunk in response.streaming_content)
        self.assertEqual(content, self.content[start:])

    def test_range_unsatisfiable_returns_416(self):
        response = self.user_client.get(
            self._url(),
            content_type="application/octet-stream",
            HTTP_RANGE=f"bytes={self.size}-",
        )

        self.assertEqual(response.status_code, 416)
        self.assertEqual(response["Content-Range"], f"bytes */{self.size}")

    def test_head_returns_headers_without_opening_stream(self):
        # Pre-populate the cached size so File.size doesn't need to open
        # the file at all, letting us assert File._file is never called.
        self.file_obj.metadata["size"] = self.size
        self.file_obj.save(update_fields=["metadata"])

        with patch.object(File, "_file") as mock_file:
            response = self.user_client.head(
                self._url(), content_type="application/octet-stream"
            )

        mock_file.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], str(self.size))
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response.content, b"")

    def test_non_seekable_backend_ignores_range(self):
        http_file = File(
            location="https://example.com/fake/remote.bam",
            name="remote.bam",
            owner=self.user,
            metadata={"size": self.size},
        )
        http_file.save()
        try:
            url = reverse("laxy_backend:file", args=[http_file.uuid()])
            # Avoid a real HTTP request - the scheme-based supports_range
            # flag (not the mock's actual seekability) drives the
            # Accept-Ranges/full-200 behaviour we're testing here.
            with patch.object(
                File, "_file", return_value=io.BytesIO(self.content)
            ):
                response = self.user_client.get(
                    url,
                    content_type="application/octet-stream",
                    HTTP_RANGE="bytes=0-9",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Accept-Ranges"], "none")
            content = b"".join(chunk for chunk in response.streaming_content)
            self.assertEqual(content, self.content)
        finally:
            http_file.delete()


class RangeRequestJobFileViewTest(TestCase):
    """
    Covers the job/<uuid>/files/<path> endpoint - the primary IGV target -
    including the ?access_token= readonly-auth path and HEAD.
    """

    def setUp(self):
        self.owner, self.owner_client = _create_user_and_login(
            "jobrangeowner", "jobrangepass"
        )

        self.content = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.size = len(self.content)

        self.job_dir = os.path.join(tempfile.gettempdir(), util.generate_uuid())
        job_output_dir = os.path.join(self.job_dir, "output")
        os.makedirs(job_output_dir, exist_ok=True)
        fd, fpath = tempfile.mkstemp(dir=job_output_dir)
        os.write(fd, self.content)
        os.close(fd)
        self.fpath = fpath

        self.file_obj = File(
            location=f"file://{fpath}",
            name=Path(fpath).name,
            path=Path(fpath).parent,
            owner_id=self.owner.id,
        )
        self.file_obj.save()

        self.compute = ComputeResource(
            host="localhost",
            status=ComputeResource.STATUS_ONLINE,
            owner=self.owner,
            disposable=False,
        )
        self.compute.save()

        input_files = FileSet()
        input_files.save()
        output_files = FileSet()
        output_files.add(self.file_obj)
        output_files.save()

        self.job = Job(
            input_files=input_files,
            output_files=output_files,
            owner=self.owner,
            compute_resource=self.compute,
        )
        self.job.save()

    def tearDown(self):
        self.job.delete()
        self.file_obj.delete()
        self.compute.delete()
        self.owner.delete()

    def _url(self):
        return reverse(
            "laxy_backend:job_file", args=[self.job.id, self.file_obj.full_path]
        )

    def test_range_via_access_token(self):
        token = AccessToken.objects.create(object_id=self.job.id).token
        client = APIClient()

        response = client.get(
            f"{self._url()}?access_token={token}", HTTP_RANGE="bytes=0-4"
        )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], f"bytes 0-4/{self.size}")
        content = b"".join(chunk for chunk in response.streaming_content)
        self.assertEqual(content, self.content[0:5])

    def test_head_via_access_token(self):
        self.file_obj.metadata["size"] = self.size
        self.file_obj.save(update_fields=["metadata"])

        token = AccessToken.objects.create(object_id=self.job.id).token
        client = APIClient()

        response = client.head(f"{self._url()}?access_token={token}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], str(self.size))
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response.content, b"")

    def test_expired_access_token_is_rejected(self):
        from datetime import timedelta
        from django.utils import timezone

        expired_at = timezone.now() - timedelta(days=1)
        token = AccessToken.objects.create(
            object_id=self.job.id, expiry_time=expired_at
        ).token
        client = APIClient()

        response = client.get(
            f"{self._url()}?access_token={token}", HTTP_RANGE="bytes=0-4"
        )

        self.assertEqual(response.status_code, 401)

    def test_traversal_location_raises(self):
        """
        Phase 2a: a File whose (tampered) location escapes the
        ComputeResource base_dir must not be servable - File._file raises
        SuspiciousFileOperation from _abs_path_on_compute before any SFTP
        connection is attempted. We mock the storage class lookup here to
        avoid needing a live SFTP host (the connection isn't otherwise
        reached, but sftp_storage's connection setup is independent of the
        traversal check, and is not the thing under test).

        Django's exception middleware special-cases SuspiciousOperation
        subclasses, converting them to a 400 response rather than letting
        them propagate (unlike other uncaught exceptions), so we assert on
        the response status rather than using assertRaises.
        """
        traversal_file = File(
            location=f"laxy+sftp://{self.compute.id}/{self.job.id}/../../../etc/passwd",
            name="passwd",
            path="/etc",
            owner_id=self.owner.id,
        )
        traversal_file.save()
        self.job.output_files.add(traversal_file)

        try:
            url = reverse(
                "laxy_backend:job_file",
                args=[self.job.id, traversal_file.full_path],
            )
            with patch.object(File, "_get_storage_class", return_value=MagicMock()):
                response = self.owner_client.get(f"{url}?download")

            self.assertEqual(response.status_code, 400)
        finally:
            traversal_file.delete()
