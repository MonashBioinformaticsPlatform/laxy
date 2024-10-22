import os
import sys
from unittest.mock import patch, MagicMock
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ..downloader import (
    get_url_cached_path,
    url_to_cache_key,
    get_urls_from_pipeline_config,
    parse_pipeline_config,
)
from laxy_downloader.cli import main as cli_main


@pytest.fixture
def temp_cache_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def mock_pipeline_config():
    return {
        "params": {
            "fetch_files": [
                {
                    "name": "file1.txt",
                    "location": "http://example.com/file1.txt",
                    "type_tags": ["tag1", "tag2"],
                },
                {
                    "name": "file2.txt",
                    "location": "http://example.com/file2.txt",
                    "type_tags": ["tag2", "tag3"],
                },
                {
                    "name": "file3.txt",
                    "location": "http://example.com/file3.txt",
                    "type_tags": ["tag1", "tag3"],
                },
            ]
        }
    }


@pytest.fixture
def pipeline_config_file(mock_pipeline_config, tmp_path):
    config_file = tmp_path / "pipeline_config.json"
    with open(config_file, "w") as f:
        json.dump(mock_pipeline_config, f)
    return config_file


def test_delete_cache_urls(temp_cache_dir):
    url1 = "http://example.com/file1.txt"
    url2 = "http://example.com/file2.txt"
    file1 = Path(temp_cache_dir) / url_to_cache_key(url1)
    file2 = Path(temp_cache_dir) / url_to_cache_key(url2)
    file1.touch()
    file2.touch()

    with patch(
        "sys.argv", ["laxydl", "delete-cached", url1, "--cache-path", temp_cache_dir]
    ):
        with patch("laxy_downloader.cli.logger") as mock_logger:
            with patch.object(sys, "exit") as mock_exit:
                cli_main()

    mock_exit.assert_called_once_with(0)
    assert not file1.exists()
    assert file2.exists()
    mock_logger.info.assert_any_call(f"Deleted cached file: {file1}")
    mock_logger.info.assert_any_call("Deleted 1 file(s) from cache.")


def test_delete_cache_pipeline_config(temp_cache_dir, pipeline_config_file):
    urls = [
        "http://example.com/file1.txt",
        "http://example.com/file2.txt",
        "http://example.com/file3.txt",
    ]
    files = [Path(temp_cache_dir) / url_to_cache_key(url) for url in urls]
    for file in files:
        file.touch()

    with patch(
        "sys.argv",
        [
            "laxydl",
            "delete-cached",
            "--pipeline-config",
            str(pipeline_config_file),
            "--cache-path",
            temp_cache_dir,
        ],
    ):
        with patch("laxy_downloader.cli.logger") as mock_logger:
            with patch.object(sys, "exit") as mock_exit:
                cli_main()

    mock_exit.assert_called_once_with(0)
    for file in files:
        assert not file.exists()
    mock_logger.info.assert_any_call("Deleted 3 file(s) from cache.")


def test_delete_cache_pipeline_config_with_type_tags(
    temp_cache_dir, pipeline_config_file
):
    urls = [
        "http://example.com/file1.txt",
        "http://example.com/file2.txt",
        "http://example.com/file3.txt",
    ]
    files = [Path(temp_cache_dir) / url_to_cache_key(url) for url in urls]
    for file in files:
        file.touch()

    with patch(
        "sys.argv",
        [
            "laxydl",
            "delete-cached",
            "--pipeline-config",
            str(pipeline_config_file),
            "--type-tags",
            "tag1,tag2",
            "--cache-path",
            temp_cache_dir,
        ],
    ):
        with patch("laxy_downloader.cli.logger") as mock_logger:
            with patch.object(sys, "exit") as mock_exit:
                cli_main()

    mock_exit.assert_called_once_with(0)
    assert not files[0].exists()
    assert files[1].exists()
    assert files[2].exists()
    mock_logger.info.assert_any_call("Deleted 1 file(s) from cache.")


def test_delete_cache_nonexistent_file(temp_cache_dir):
    url = "http://example.com/nonexistent.txt"

    with patch(
        "sys.argv", ["laxydl", "delete-cached", url, "--cache-path", temp_cache_dir]
    ):
        with patch("laxy_downloader.cli.logger") as mock_logger:
            with patch.object(sys, "exit") as mock_exit:
                cli_main()

    mock_exit.assert_called_once_with(0)
    mock_logger.info.assert_any_call(
        f"File not found in cache: {get_url_cached_path(url, temp_cache_dir)}"
    )
    mock_logger.info.assert_any_call("Deleted 0 file(s) from cache.")
