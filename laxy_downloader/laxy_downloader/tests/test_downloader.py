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

    with pytest.raises(
        Exception, match="Downloaded file size .* does not match Content-Length"
    ):
        download_url(url, file_path)


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


if __name__ == "__main__":
    pytest.main([__file__])
