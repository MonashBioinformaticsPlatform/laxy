import os
import tempfile
import hashlib
from unittest import mock
from pathlib import Path

import pytest
import requests

from ..downloader import download_url, get_content_length


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


@mock.patch("laxy_downloader.downloader.request_with_retries")
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


@mock.patch("laxy_downloader.downloader.request_with_retries")
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


@mock.patch("laxy_downloader.downloader.request_with_retries")
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
    mock_request.assert_called_with("GET", url, stream=True, headers={}, auth=mock.ANY)
    assert isinstance(mock_request.call_args[1]["auth"], requests.auth.HTTPBasicAuth)


@mock.patch("laxy_downloader.downloader.request_with_retries")
def test_download_url_incomplete_file(mock_request, temp_dir):
    url = "http://example.com/incomplete_file.txt"
    content = b"This file will be incomplete."
    mock_response = create_mock_response(
        content[:15], headers={"content-length": str(len(content))}
    )
    mock_request.return_value = mock_response

    file_path = os.path.join(temp_dir, "incomplete_file.txt")

    # The test should expect the original exception message, not the cleanup error
    with pytest.raises(Exception) as exc_info:
        download_url(url, file_path)
    
    # Check that the exception message contains the expected content
    assert "Downloaded file size" in str(exc_info.value)
    assert "does not match Content-Length" in str(exc_info.value)


@mock.patch("laxy_downloader.downloader.request_with_retries")
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
    mock_request.assert_called_once_with("HEAD", url, headers={}, auth=None)


@mock.patch("laxy_downloader.downloader.request_with_retries")
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


@mock.patch("laxy_downloader.downloader.request_with_retries")
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


@mock.patch("laxy_downloader.downloader.request_with_retries")
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


@mock.patch("laxy_downloader.downloader.request_with_retries")
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


@mock.patch("laxy_downloader.downloader.request_with_retries")
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


if __name__ == "__main__":
    pytest.main([__file__])
