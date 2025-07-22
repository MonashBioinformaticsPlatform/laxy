#!/usr/bin/env python3

import os
import tempfile
import json
from unittest import mock
from pathlib import Path

import pytest

from ..cli import add_commandline_args
from ..downloader import parse_pipeline_config, get_urls_from_pipeline_config


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def sample_pipeline_config(temp_dir):
    """Create a sample pipeline config file for testing."""
    config_data = {
        "id": "test-config",
        "sample_cart": {
            "samples": [
                {
                    "name": "test_sample",
                    "files": [
                        {
                            "R1": "ftp://example.com/test1.fastq.gz",
                            "type_tags": ["fastq", "input"]
                        },
                        {
                            "R2": "ftp://example.com/test2.fastq.gz",
                            "type_tags": ["fastq", "input"]
                        }
                    ]
                }
            ]
        }
    }
    
    config_file = os.path.join(temp_dir, "pipeline_config.json")
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    
    return config_file


def test_expire_cache_pipeline_config_parsing(sample_pipeline_config):
    """Test that the expire-cache command can parse pipeline config files."""
    # Test that parse_pipeline_config can read the file
    with open(sample_pipeline_config, 'r') as f:
        config = parse_pipeline_config(f)
    
    # Test that get_urls_from_pipeline_config can extract URLs
    url_filenames = get_urls_from_pipeline_config(config)
    
    expected_urls = {
        "ftp://example.com/test1.fastq.gz",
        "ftp://example.com/test2.fastq.gz"
    }
    
    assert set(url_filenames.keys()) == expected_urls


def test_expire_cache_pipeline_config_with_type_tags(sample_pipeline_config):
    """Test that the expire-cache command can filter by type tags."""
    with open(sample_pipeline_config, 'r') as f:
        config = parse_pipeline_config(f)
    
    # Test filtering by type tag
    url_filenames = get_urls_from_pipeline_config(config, required_type_tags=["fastq"])
    
    expected_urls = {
        "ftp://example.com/test1.fastq.gz",
        "ftp://example.com/test2.fastq.gz"
    }
    
    assert set(url_filenames.keys()) == expected_urls
    
    # Test filtering by multiple type tags
    url_filenames = get_urls_from_pipeline_config(config, required_type_tags=["fastq", "input"])
    
    assert set(url_filenames.keys()) == expected_urls
    
    # Test filtering by non-existent type tag - this should return empty dict
    url_filenames = get_urls_from_pipeline_config(config, required_type_tags=["nonexistent"])
    
    assert len(url_filenames) == 0


def test_expire_cache_cli_parser(temp_dir):
    """Test that the CLI parser includes the new pipeline-config option for expire-cache."""
    import argparse
    
    # Create a temporary config file for testing
    config_file = os.path.join(temp_dir, "test.json")
    with open(config_file, 'w') as f:
        json.dump({"test": "data"}, f)
    
    parser = argparse.ArgumentParser()
    parser = add_commandline_args(parser)
    
    # Test that we can parse expire-cache with pipeline-config
    args = parser.parse_args([
        "expire-cache",
        "--pipeline-config", config_file,
        "--type-tags", "fastq,input"
    ])
    
    assert args.command == "expire-cache"
    assert args.pipeline_config is not None
    assert args.type_tags == ["fastq", "input"]


def test_expire_cache_cli_parser_urls_and_pipeline_config(temp_dir):
    """Test that the CLI parser can handle both URLs and pipeline-config."""
    import argparse
    
    # Create a temporary config file for testing
    config_file = os.path.join(temp_dir, "test.json")
    with open(config_file, 'w') as f:
        json.dump({"test": "data"}, f)
    
    parser = argparse.ArgumentParser()
    parser = add_commandline_args(parser)
    
    # Test that we can parse expire-cache with both URLs and pipeline-config
    args = parser.parse_args([
        "expire-cache",
        "http://example.com/file1.txt",
        "http://example.com/file2.txt",
        "--pipeline-config", config_file,
        "--type-tags", "fastq"
    ])
    
    assert args.command == "expire-cache"
    assert args.urls == ["http://example.com/file1.txt", "http://example.com/file2.txt"]
    assert args.pipeline_config is not None
    assert args.type_tags == ["fastq"] 