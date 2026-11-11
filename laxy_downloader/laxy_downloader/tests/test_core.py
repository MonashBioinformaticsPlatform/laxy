import os
import tempfile
import hashlib
from unittest import mock
from pathlib import Path

import pytest
import requests

from ..core import (
    HTTP_TIMEOUT,
    apply_existing_download_decision,
    classify_aria_round,
    decide_existing_download,
    download_url,
    get_content_length,
)


# Helper function to create a mock response with custom content
def create_mock_response(content, status_code=200, headers=None):
    mock_response = mock.Mock()
    mock_response.status_code = status_code
    mock_response.headers = headers or {}
    mock_response.iter_content.return_value = [
        content[i : i + 1024] for i in range(0, len(content), 1024)
    ]
    mock_response.raise_for_status = mock.Mock()
    return mock_response


# Helper function to calculate MD5 hash of a file
def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch):
    monkeypatch.setattr("laxy_downloader.core.time.sleep", lambda seconds: None)


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_small_file(mock_request, temp_dir):
    url = "http://example.com/small_file.txt"
    content = b"This is a small file for testing."
    mock_response = create_mock_response(
        content, headers={"content-length": str(len(content))}
    )
    mock_request.return_value = mock_response

    file_path = os.path.join(temp_dir, "small_file.txt")
    result = download_url(url, file_path)

    assert result == file_path
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_large_file(mock_request, temp_dir):
    url = "http://example.com/large_file.bin"
    content = os.urandom(1024 * 1024 * 5)  # 5 MB random content
    mock_response = create_mock_response(
        content, headers={"content-length": str(len(content))}
    )
    mock_request.return_value = mock_response

    file_path = os.path.join(temp_dir, "large_file.bin")
    result = download_url(url, file_path)

    assert result == file_path
    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) == len(content)
    assert calculate_md5(file_path) == hashlib.md5(content).hexdigest()


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_with_auth(mock_request, temp_dir):
    url = "http://example.com/auth_file.txt"
    content = b"This file requires authentication."
    mock_response = create_mock_response(
        content, headers={"content-length": str(len(content))}
    )
    mock_request.return_value = mock_response

    file_path = os.path.join(temp_dir, "auth_file.txt")
    result = download_url(url, file_path, username="user", password="pass")

    assert result == file_path
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content

    # Check if the auth was passed correctly
    mock_request.assert_called_with(
        "GET",
        url,
        stream=True,
        headers={"Accept-Encoding": "identity"},
        auth=mock.ANY,
        timeout=HTTP_TIMEOUT,
    )
    assert isinstance(mock_request.call_args[1]["auth"], requests.auth.HTTPBasicAuth)


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_incomplete_file(mock_request, temp_dir):
    url = "http://example.com/incomplete_file.txt"
    content = b"This file will be incomplete."
    mock_response = create_mock_response(
        content[:15], headers={"content-length": str(len(content))}
    )
    mock_request.return_value = mock_response

    file_path = os.path.join(temp_dir, "incomplete_file.txt")

    with pytest.raises(Exception) as exc_info:
        download_url(url, file_path, max_retries=3)

    assert "Downloaded file size" in str(exc_info.value)
    assert "does not match Content-Length" in str(exc_info.value)
    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) == 15


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_existing_file(mock_request, temp_dir):
    url = "http://example.com/existing_file.txt"
    content = b"This file already exists."
    file_path = os.path.join(temp_dir, "existing_file.txt")

    # Create an existing file
    with open(file_path, "wb") as f:
        f.write(content)

    # Mock the HEAD request for content length
    mock_head_response = mock.Mock()
    mock_head_response.headers = {"content-length": str(len(content))}
    mock_request.return_value = mock_head_response

    result = download_url(url, file_path, check_existing_size=True)

    assert result == file_path
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content

    # Ensure no GET request was made (only HEAD)
    mock_request.assert_called_once_with(
        "HEAD", url, headers={"Accept-Encoding": "identity"}, auth=None
    )


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_resume_partial_download(mock_request, temp_dir):
    url = "http://example.com/partial_file.txt"
    content = b"This is a complete file that will be downloaded in parts."
    file_path = os.path.join(temp_dir, "partial_file.txt")

    # Mock HEAD request
    mock_head_response = mock.Mock()
    mock_head_response.headers = {"content-length": str(len(content))}
    
    # First attempt - partial download
    mock_partial_response = create_mock_response(
        content[:20],
        headers={"content-length": str(len(content))}
    )
    
    # Second attempt - range request response
    mock_range_response = create_mock_response(
        content[20:],
        status_code=206,  # Partial Content status code
        headers={
            "content-length": str(len(content[20:])),
            "content-range": f"bytes 20-{len(content)-1}/{len(content)}"
        }
    )
    
    mock_request.side_effect = [
        mock_head_response,
        mock_partial_response,
        mock_range_response
    ]

    result = download_url(url, file_path)

    assert result == file_path
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content

    # Check that the range request was made correctly
    calls = mock_request.call_args_list
    assert len(calls) == 3
    assert calls[0][0] == ("HEAD", url)  # First call is HEAD request
    assert calls[1][0] == ("GET", url)   # Second call is initial GET
    assert calls[2][0] == ("GET", url)   # Third call is range request
    assert calls[2][1]["headers"]["Range"] == "bytes=20-"  # Check range header


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_multiple_resume_attempts(mock_request, temp_dir):
    url = "http://example.com/partial_file.txt"
    content = b"This is a file that will need multiple resume attempts to complete."
    file_path = os.path.join(temp_dir, "partial_file.txt")

    # Mock HEAD request
    mock_head_response = mock.Mock()
    mock_head_response.headers = {"content-length": str(len(content))}

    # Create responses for partial downloads
    responses = [
        # HEAD request
        mock_head_response,
        # First attempt - gets first 10 bytes
        create_mock_response(
            content[:10],
            headers={"content-length": str(len(content))}
        ),
        # Second attempt - gets next 15 bytes with range request
        create_mock_response(
            content[10:25],
            status_code=206,
            headers={
                "content-length": str(len(content[10:25])),
                "content-range": f"bytes 10-24/{len(content)}"
            }
        ),
        # Final attempt - gets remaining bytes with range request
        create_mock_response(
            content[25:],
            status_code=206,
            headers={
                "content-length": str(len(content[25:])),
                "content-range": f"bytes 25-{len(content)-1}/{len(content)}"
            }
        )
    ]

    mock_request.side_effect = responses

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content

    calls = mock_request.call_args_list
    assert calls[0][0] == ("HEAD", url)
    assert calls[2][1]["headers"]["Range"] == "bytes=10-"
    assert calls[3][1]["headers"]["Range"] == "bytes=25-"


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_server_ignores_range(mock_request, temp_dir):
    """Test behavior when server ignores range requests and sends full file"""
    url = "http://example.com/partial_file.txt"
    content = b"This is a file where the server ignores range requests."
    file_path = os.path.join(temp_dir, "partial_file.txt")

    # Mock HEAD request
    mock_head_response = mock.Mock()
    mock_head_response.headers = {"content-length": str(len(content))}

    # First attempt - partial download
    mock_partial_response = create_mock_response(
        content[:20],
        headers={"content-length": str(len(content))}
    )

    # Second attempt - server ignores range and sends full file
    mock_full_response = create_mock_response(
        content,
        status_code=200,  # Server ignores range and sends full file
        headers={
            "content-length": str(len(content)),
            # Add Accept-Ranges header to indicate server supports ranges
            "Accept-Ranges": "bytes"
        }
    )

    # Add an extra mock response in case we need another retry
    mock_request.side_effect = [
        mock_head_response,
        mock_partial_response,
        mock_full_response,
        mock_full_response  # Extra response just in case
    ]

    result = download_url(url, file_path)

    assert result == file_path
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content

    # Verify the sequence of requests
    calls = mock_request.call_args_list
    assert 2 <= len(calls) <= 4  # Allow for 2-4 calls
    assert calls[0][0] == ("HEAD", url)
    assert calls[1][0] == ("GET", url)
    if len(calls) > 2:
        assert calls[2][0] == ("GET", url)
        assert "Range" in calls[2][1]["headers"]
    if len(calls) > 3:
        assert calls[3][0] == ("GET", url)
        assert "Range" in calls[3][1]["headers"]


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_range_416_falls_back_to_full_download(mock_request, temp_dir):
    """A CDN with a stale Range-serving cache can 416 a resume request even
    though full (non-Range) downloads succeed - eg jsDelivr serving a mutable
    git branch ref where the byte-range cache hasn't caught up with a recent
    push. The client should discard the local file and retry with a full
    download rather than failing the whole job."""
    url = "http://example.com/moved_goalposts.txt"
    content = b"This is the current, correct, full content of the file."
    file_path = os.path.join(temp_dir, "moved_goalposts.txt")

    mock_head_response = mock.Mock()
    mock_head_response.headers = {"content-length": str(len(content))}

    # First attempt - gets a short, stale response (eg from a CDN edge whose
    # full-object cache hasn't updated yet), which looks "partial" since it
    # doesn't match Content-Length from the HEAD.
    mock_stale_response = create_mock_response(
        content[:10],
        headers={"content-length": str(len(content))},
    )

    # Second attempt - resumes via Range from the stale partial file, but the
    # CDN's Range-serving cache thinks the resource is only 10 bytes long, so
    # any Range starting at/after that is invalid.
    mock_416_response = mock.Mock()
    mock_416_response.status_code = 416
    mock_416_response.headers = {}
    mock_416_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_416_response
    )

    # Third attempt - local file was discarded, so this is a fresh full
    # download (no Range header) that succeeds with the correct content.
    mock_full_response = create_mock_response(
        content, headers={"content-length": str(len(content))}
    )

    mock_request.side_effect = [
        mock_head_response,
        mock_stale_response,
        mock_416_response,
        mock_full_response,
    ]

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content

    calls = mock_request.call_args_list
    assert len(calls) == 4
    assert calls[0][0] == ("HEAD", url)
    assert calls[1][0] == ("GET", url)
    assert "Range" not in calls[1][1]["headers"]
    assert calls[2][0] == ("GET", url)
    assert calls[2][1]["headers"]["Range"] == "bytes=10-"
    assert calls[3][0] == ("GET", url)
    assert "Range" not in calls[3][1]["headers"]  # discarded partial, fresh start


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_no_content_length(mock_request, temp_dir):
    url = "http://example.com/no_length.txt"
    content = b"This file has no Content-Length header."
    file_path = os.path.join(temp_dir, "no_length.txt")

    # Mock HEAD request with no content-length
    mock_head_response = mock.Mock()
    mock_head_response.headers = {}
    mock_head_response.raise_for_status = mock.Mock()

    # Mock GET response
    mock_response = create_mock_response(
        content,
        headers={},  # No content-length header
    )

    mock_request.side_effect = [mock_head_response, mock_response]

    result = download_url(url, file_path)

    assert result == file_path
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == content


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_lock_file_cleanup(mock_request, temp_dir):
    """Test that lock files are properly cleaned up after download completion or failure."""
    url = "http://example.com/test_file.txt"
    content = b"Test content for lock file cleanup"
    file_path = os.path.join(temp_dir, "test_file.txt")
    lock_path = f"{file_path}.lock"

    # Test successful download
    mock_response = create_mock_response(
        content, headers={"content-length": str(len(content))}
    )
    mock_request.return_value = mock_response

    result = download_url(url, file_path)
    assert result == file_path
    assert os.path.exists(file_path)
    assert not os.path.exists(lock_path), "Lock file should be removed after successful download"

    # Test failed download
    mock_request.side_effect = requests.exceptions.RequestException("Download failed")
    
    with pytest.raises(requests.exceptions.RequestException):
        download_url(url, file_path)
    
    assert not os.path.exists(lock_path), "Lock file should be removed after failed download"

    # Test download interrupted by keyboard interrupt
    mock_request.side_effect = KeyboardInterrupt()
    
    with pytest.raises(KeyboardInterrupt):
        download_url(url, file_path)
    
    assert not os.path.exists(lock_path), "Lock file should be removed after keyboard interrupt"


def _head_response(content_length=None, ok=True):
    mock_head = mock.Mock()
    mock_head.ok = ok
    mock_head.status_code = 200 if ok else 405
    headers = {}
    if content_length is not None:
        headers["content-length"] = str(content_length)
    mock_head.headers = headers
    mock_head.raise_for_status = mock.Mock()
    return mock_head


def _http_error_response(status_code):
    mock_response = mock.Mock()
    mock_response.status_code = status_code
    mock_response.headers = {}
    error = requests.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = error
    return mock_response


def _iter_then_error(data, error):
    def _iter(chunk_size=1024):
        yield data
        raise error

    return _iter


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_resumes_existing_short_file(mock_request, temp_dir):
    url = "http://example.com/resume_existing.txt"
    content = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    file_path = os.path.join(temp_dir, "resume_existing.txt")
    with open(file_path, "wb") as f:
        f.write(content[:10])

    mock_request.side_effect = [
        _head_response(len(content)),
        create_mock_response(
            content[10:],
            status_code=206,
            headers={
                "content-length": str(len(content[10:])),
                "content-range": f"bytes 10-{len(content) - 1}/{len(content)}",
            },
        ),
    ]

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content
    calls = mock_request.call_args_list
    assert calls[1][1]["headers"]["Range"] == "bytes=10-"
    assert calls[1][1]["timeout"] == HTTP_TIMEOUT


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_replaces_oversized_file(mock_request, temp_dir):
    url = "http://example.com/oversized.txt"
    content = b"short"
    file_path = os.path.join(temp_dir, "oversized.txt")
    with open(file_path, "wb") as f:
        f.write(content + b"EXTRA")

    mock_request.side_effect = [
        _head_response(len(content)),
        create_mock_response(content, headers={"content-length": str(len(content))}),
    ]

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content
    assert "Range" not in mock_request.call_args_list[1][1]["headers"]


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_midstream_chunked_encoding_error(mock_request, temp_dir):
    url = "http://example.com/dropped.txt"
    content = b"0123456789abcdefghij"
    file_path = os.path.join(temp_dir, "dropped.txt")

    dropped = create_mock_response(
        content[:8], headers={"content-length": str(len(content))}
    )
    dropped.iter_content.side_effect = _iter_then_error(
        content[:8], requests.exceptions.ChunkedEncodingError("cut off")
    )

    remaining = create_mock_response(
        content[8:],
        status_code=206,
        headers={
            "content-length": str(len(content[8:])),
            "content-range": f"bytes 8-{len(content) - 1}/{len(content)}",
        },
    )

    mock_request.side_effect = [_head_response(len(content)), dropped, remaining]

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content
    assert mock_request.call_args_list[2][1]["headers"]["Range"] == "bytes=8-"


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_midstream_read_timeout(mock_request, temp_dir):
    url = "http://example.com/timeout.txt"
    content = b"timeout-resume-content!"
    file_path = os.path.join(temp_dir, "timeout.txt")

    timed_out = create_mock_response(
        content[:6], headers={"content-length": str(len(content))}
    )
    timed_out.iter_content.side_effect = _iter_then_error(
        content[:6], requests.exceptions.ReadTimeout("stalled")
    )

    remaining = create_mock_response(
        content[6:],
        status_code=206,
        headers={
            "content-length": str(len(content[6:])),
            "content-range": f"bytes 6-{len(content) - 1}/{len(content)}",
        },
    )

    mock_request.side_effect = [_head_response(len(content)), timed_out, remaining]

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_permanent_404_does_not_retry(mock_request, temp_dir):
    url = "http://example.com/missing.txt"
    file_path = os.path.join(temp_dir, "missing.txt")
    mock_request.side_effect = [_head_response(12), _http_error_response(404)]

    with pytest.raises(requests.exceptions.HTTPError):
        download_url(url, file_path, max_retries=5)

    get_calls = [c for c in mock_request.call_args_list if c[0][0] == "GET"]
    assert len(get_calls) == 1


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_retries_503(mock_request, temp_dir):
    url = "http://example.com/flaky.txt"
    content = b"recovered after 503"
    file_path = os.path.join(temp_dir, "flaky.txt")
    mock_request.side_effect = [
        _head_response(len(content)),
        _http_error_response(503),
        create_mock_response(
            content, headers={"content-length": str(len(content))}
        ),
    ]

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content
    get_calls = [c for c in mock_request.call_args_list if c[0][0] == "GET"]
    assert len(get_calls) == 2


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_no_progress_stops(mock_request, temp_dir):
    url = "http://example.com/stuck.txt"
    content = b"0123456789"
    file_path = os.path.join(temp_dir, "stuck.txt")
    short = create_mock_response(
        content[:3], headers={"content-length": str(len(content))}
    )
    mock_request.side_effect = [_head_response(len(content))] + [short] * 10

    with pytest.raises(Exception) as exc_info:
        download_url(url, file_path, max_retries=20, no_progress_max=3)

    assert "no progress" in str(exc_info.value)
    get_calls = [c for c in mock_request.call_args_list if c[0][0] == "GET"]
    # first attempt writes 3 bytes (progress), then 3 consecutive no-progress
    assert len(get_calls) == 4
    assert os.path.exists(file_path)


@mock.patch("laxy_downloader.core.request_with_retries")
def test_download_url_uses_get_content_length_when_head_omits_it(
    mock_request, temp_dir
):
    url = "http://example.com/no_head_length.txt"
    content = b"size comes from GET"
    file_path = os.path.join(temp_dir, "no_head_length.txt")

    short = create_mock_response(
        content[:5],
        headers={"content-length": str(len(content))},
    )
    rest = create_mock_response(
        content[5:],
        status_code=206,
        headers={
            "content-length": str(len(content[5:])),
            "content-range": f"bytes 5-{len(content) - 1}/{len(content)}",
        },
    )
    mock_request.side_effect = [_head_response(None), short, rest]

    result = download_url(url, file_path)

    assert result == file_path
    with open(file_path, "rb") as f:
        assert f.read() == content


def test_decide_existing_download_skip_when_sizes_match():
    assert (
        decide_existing_download(
            skip_existing=True,
            destination_exists=True,
            destination_is_symlink=True,
            destination_size=100,
            cache_exists=True,
            cache_size=100,
            aria2_control_exists=False,
            content_length=100,
        )
        == "skip"
    )


def test_decide_existing_download_resume_when_cache_short():
    assert (
        decide_existing_download(
            skip_existing=True,
            destination_exists=True,
            destination_is_symlink=True,
            destination_size=40,
            cache_exists=True,
            cache_size=40,
            aria2_control_exists=False,
            content_length=100,
        )
        == "resume"
    )


def test_decide_existing_download_resume_when_aria2_control_present():
    assert (
        decide_existing_download(
            skip_existing=True,
            destination_exists=True,
            destination_is_symlink=True,
            destination_size=100,
            cache_exists=True,
            cache_size=100,
            aria2_control_exists=True,
            content_length=100,
        )
        == "resume"
    )


def test_decide_existing_download_replace_oversized_cache():
    assert (
        decide_existing_download(
            skip_existing=True,
            destination_exists=True,
            destination_is_symlink=False,
            destination_size=150,
            cache_exists=True,
            cache_size=150,
            aria2_control_exists=False,
            content_length=100,
        )
        == "replace_cache"
    )


def test_decide_existing_download_copy_short_destination_to_cache():
    assert (
        decide_existing_download(
            skip_existing=True,
            destination_exists=True,
            destination_is_symlink=False,
            destination_size=40,
            cache_exists=False,
            cache_size=None,
            aria2_control_exists=False,
            content_length=100,
        )
        == "copy_dest_to_cache"
    )


def test_apply_existing_download_decision_keeps_short_cache(temp_dir):
    cache_file = os.path.join(temp_dir, "cached")
    dest = os.path.join(temp_dir, "sample.fastq.gz")
    with open(cache_file, "wb") as f:
        f.write(b"partial")
    os.symlink(cache_file, dest)

    apply_existing_download_decision(
        "resume", destination_path=dest, cache_file=cache_file
    )

    assert os.path.exists(cache_file)
    assert os.path.getsize(cache_file) == 7
    assert not os.path.lexists(dest)


def test_apply_existing_download_decision_copies_dest_to_cache(temp_dir):
    cache_file = os.path.join(temp_dir, "cached")
    dest = os.path.join(temp_dir, "sample.fastq.gz")
    with open(dest, "wb") as f:
        f.write(b"partial-bytes")

    apply_existing_download_decision(
        "copy_dest_to_cache", destination_path=dest, cache_file=cache_file
    )

    assert os.path.exists(cache_file)
    with open(cache_file, "rb") as f:
        assert f.read() == b"partial-bytes"
    assert not os.path.lexists(dest)


def test_classify_aria_round_requeues_transient_error():
    result = classify_aria_round(
        [
            {
                "url": "http://example.com/a",
                "status": "error",
                "errorCode": "1",
                "cache_size": 10,
                "content_length": 100,
            }
        ],
        round_index=0,
        max_rounds=6,
    )
    assert result["requeue"] == ["http://example.com/a"]
    assert result["failed"] == []
    assert result["ok"] == []


def test_classify_aria_round_fails_permanent_error():
    result = classify_aria_round(
        [
            {
                "url": "http://example.com/missing",
                "status": "error",
                "errorCode": "3",
                "cache_size": None,
                "content_length": 100,
            }
        ],
        round_index=0,
        max_rounds=6,
    )
    assert result["failed"] == ["http://example.com/missing"]
    assert result["requeue"] == []


def test_classify_aria_round_requeues_complete_but_short():
    result = classify_aria_round(
        [
            {
                "url": "http://example.com/short",
                "status": "complete",
                "errorCode": "0",
                "cache_size": 50,
                "content_length": 100,
            }
        ],
        round_index=0,
        max_rounds=6,
    )
    assert result["requeue"] == ["http://example.com/short"]


def test_classify_aria_round_fails_after_six_rounds():
    items = [
        {
            "url": "http://example.com/still-short",
            "status": "complete",
            "errorCode": "0",
            "cache_size": 50,
            "content_length": 100,
        }
    ]
    last = classify_aria_round(items, round_index=5, max_rounds=6)
    assert last["failed"] == ["http://example.com/still-short"]
    assert last["requeue"] == []
    assert last["exhausted"] is True


if __name__ == "__main__":
    pytest.main([__file__])
