#!/usr/bin/env python3
import cgi
import json
import ssl
import urllib
from contextlib import closing
from urllib.parse import urlparse, urlsplit, urlunsplit, unquote
from pathlib import Path
import shutil
from typing import (
    Dict,
    Iterable,
    List,
    Sequence,
    Tuple,
    Union,
    Mapping,
    Set,
    Callable,
    Optional,
)
import logging
import sys
import os
import argparse
import time
import subprocess
import random
import string
import tempfile
import platform
import tarfile
from functools import partial
import concurrent.futures
from http.client import responses as response_codes
from base64 import urlsafe_b64encode
import functools
from collections import OrderedDict

import re
import unicodedata
from text_unidecode import unidecode

from . import pymmh3 as mmh3

import requests
import backoff
from toolz.dicttoolz import merge as merge_dicts
from requests.auth import HTTPBasicAuth
import magic
import trio
import asks
from attrdict import AttrDict
from filelock import FileLock
from contextlib import contextmanager

logger = logging.getLogger(__name__)
# logging.basicConfig(format='%(levelname)s: %(asctime)s -- %(message)s', level=logging.INFO)

asks.init(trio)


def get_tmpdir():
    return "/tmp" if platform.system() == "Darwin" else tempfile.gettempdir()


def get_default_cache_path():
    return os.path.join(get_tmpdir(), "laxy_downloader_cache")


def url_to_cache_key(url):
    if is_tar_url_with_fragment(url):
        url = remove_url_fragment(url)

    """
    Takes a URL and returns a short filename-safe key.

    A URL hashed with Murmur3 and base64 encoded into a constant length (22 character)
    string. We use Murmur3 since it is supposed to have very few collisions for short
    strings.
    """
    return (
        urlsafe_b64encode(mmh3.hash128(url).to_bytes(16, byteorder="big", signed=False))
        .decode("ascii")
        .rstrip("=")
    )


def get_url_cached_path(url, cache_path):
    return os.path.join(cache_path, url_to_cache_key(url))


def _raise_request_exception(response):
    e = requests.exceptions.RequestException(response=response)
    e.message = "Request failed (%s) %s : %s" % (
        response.status_code,
        response.reason,
        response.url,
    )
    raise e


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, urllib.error.URLError),
    max_tries=8,
    jitter=backoff.full_jitter,
)
def request_with_retries(*args, **kwargs):
    """
    A wrapper around requests.requests.
    Make an HTTP request, but retry and don't give up easily in the face of
    common temporary failures.

    :param args: The args for requests.request
                 (eg, 'GET', 'http://www.example.com')
    :type args:
    :param kwargs: The keyword args for requests.request
                   eg headers={'Authorization': 'asdfghjkl'}
    :type kwargs:
    :return: The requests response object.
    :rtype: requests.Response
    """

    url = args[1]
    scheme = urlparse(url)
    if scheme in ["ftp", "ftps", "data"]:
        return urllib.request.urlopen(url)

    # headers = copy(global_headers)
    headers = {}
    extra_headers = kwargs.get("headers", None)
    if extra_headers:
        kwargs["headers"] = merge_dicts(headers, extra_headers)

    try:
        response = requests.request(*args, **kwargs)
        # 502 Bad Gateway triggers retries - this is a common status
        # code when a reverse proxied web app behind Nginx or Apache is
        # temporarily restarting
        if response.status_code == 502:
            _raise_request_exception(response)

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None:
            logger.error(
                "Request failed (%s) %s : %s",
                e.response.status_code,
                e.response.reason,
                e.response.url,
            )
        else:
            logger.error(
                "Request failed : an exception occurred and the web "
                "request was not made."
            )
        raise e

    return response


@contextmanager
def temporary_file(mode="wb", dir=None, prefix=None, suffix=None):
    tmp = tempfile.NamedTemporaryFile(
        mode=mode, dir=dir, prefix=prefix, suffix=suffix, delete=False
    )
    try:
        yield tmp
    finally:
        tmp.close()


def download_url(
    url: str,
    filepath: Union[str, Path],
    headers: Optional[Dict[str, str]] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    tmp_directory: Optional[str] = None,
    cleanup_on_exception: bool = True,
    check_existing_size: bool = True,
    remove_existing: bool = True,
    chunk_size: int = 1024 * 1024,  # 1Mb chunk size
    max_retries: int = 3,
) -> str:
    """
    Download a file from a given URL to a specified filepath, with support for both HTTP(S) and FTP protocols.

    This function implements file locking to ensure thread-safety when multiple processes
    attempt to download the same file. It also supports checking and removing existing files,
    as well as cleaning up temporary files in case of exceptions.

    Args:
        url (str): The URL of the file to download.
        filepath (str): The local path where the downloaded file should be saved.
        headers (Optional[Dict[str, str]]): Additional HTTP headers to send with the request.
        username (Optional[str]): Username for basic authentication.
        password (Optional[str]): Password for basic authentication.
        tmp_directory (Optional[str]): Directory to use for temporary files. If None, uses the parent directory of filepath.
        cleanup_on_exception (bool): Whether to remove temporary files if an exception occurs during download.
        check_existing_size (bool): Whether to check the size of an existing file before downloading.
        remove_existing (bool): Whether to remove an existing file if its size doesn't match the expected size.
        chunk_size (int): The size of chunks to use when streaming the download.
        max_retries (int): The maximum number of retry attempts for the download.

    Returns:
        str: The path to the downloaded file.

    Raises:
        Exception: If the download fails or if the downloaded file is incomplete.
    """
    auth = None
    if username is not None and password is not None:
        auth = HTTPBasicAuth(username, password)

    headers = headers or {}
    filepath = Path(filepath)
    directory = tmp_directory or str(filepath.parent)
    filename = filepath.name
    filepath = str(filepath)
    scheme = urlparse(url).scheme.lower()

    lock_path = f"{filepath}.lock"
    lock = FileLock(lock_path, timeout=60 * 60 * 12)  # 12 hours timeout
    tmpfile_path = None

    try:
        with lock:
            content_length = get_content_length(url, headers, auth, scheme)

            if check_existing_size and os.path.exists(filepath):
                if content_length is not None and os.path.getsize(filepath) == int(
                    content_length
                ):
                    logger.info(
                        f"File of correct size {filepath} ({content_length} bytes) already exists, skipping download"
                    )
                    return filepath
                elif remove_existing:
                    logger.info(
                        f"File exists {filepath} but is incorrect size ({content_length} bytes). Deleting existing file."
                    )
                    os.remove(filepath)

            for attempt in range(max_retries):
                logger.info(
                    f"Starting download (attempt {attempt + 1}/{max_retries}): {url} ({url_to_cache_key(url)})"
                )

                # Get size of partial download if it exists
                partial_size = (
                    os.path.getsize(filepath) if os.path.exists(filepath) else None
                )

                with temporary_file(
                    mode="wb", dir=directory, prefix=f"{filename}.", suffix=".tmp"
                ) as tmpfile:
                    tmpfile_path = tmpfile.name
                    if partial_size is not None:
                        # Copy existing partial download
                        shutil.copy2(filepath, tmpfile.name)

                    if scheme == "ftp":
                        urllib.request.urlretrieve(url, filename=tmpfile.name)
                    else:
                        request_headers = headers.copy()
                        if partial_size is not None and partial_size > 0:
                            request_headers["Range"] = f"bytes={partial_size}-"

                        with closing(
                            request_with_retries(
                                "GET",
                                url,
                                stream=True,
                                headers=request_headers,
                                auth=auth,
                            )
                        ) as download:
                            download.raise_for_status()

                            # If server ignored our range request and sent full file
                            if partial_size and download.status_code == 200:
                                mode = "wb"  # Start fresh since we got the full file
                            else:
                                mode = "ab" if partial_size else "wb"

                            with open(tmpfile.name, mode) as f:
                                for chunk in download.iter_content(
                                    chunk_size=chunk_size
                                ):
                                    f.write(chunk)
                                f.flush()
                                os.fsync(f.fileno())

                    # Check if download is complete
                    file_size = os.path.getsize(tmpfile.name)
                    if content_length is None or file_size == int(content_length):
                        shutil.move(tmpfile.name, filepath)
                        return filepath
                    else:
                        # Save partial download for next attempt
                        shutil.move(tmpfile.name, filepath)
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Downloaded file size ({file_size}) does not match Content-Length ({content_length}). Retrying..."
                            )
                        else:
                            raise Exception(
                                f"Downloaded file size ({file_size}) does not match Content-Length ({content_length}) after {max_retries} attempts."
                            )

    except Exception as e:
        handle_download_exception(
            e, getattr(e, "status_code", None), url, cleanup_on_exception, tmpfile_path
        )
        raise  # Re-raise the exception after cleanup
    finally:
        # Clean up the lock file if it exists
        try:
            if os.path.exists(lock_path):
                os.unlink(lock_path)
        except OSError as e:
            logger.warning(f"Failed to remove lock file {lock_path}: {e}")


def get_content_length(url, headers, auth, scheme):
    """
    Get the content length of a file from a given URL.

    Args:
        url (str): The URL of the file.
        headers (dict): Additional HTTP headers to send with the request.
        auth (requests.auth.HTTPBasicAuth): Authentication credentials.
        scheme (str): The scheme of the URL (http, https or ftp).

    Returns:
        Optional[int]: The content length if available, None otherwise.
    """
    if scheme == "ftp":
        with closing(urllib.request.urlopen(url)) as response:
            return response.info().get("Content-Length", None)
    else:
        with closing(
            request_with_retries("HEAD", url, headers=headers, auth=auth)
        ) as head_request:
            return head_request.headers.get("content-length", None)


def handle_download_exception(e, status_code, url, cleanup_on_exception, tmpfilepath):
    if status_code:
        logger.error(
            f"Download failed ({status_code} {response_codes[status_code]}): {url}"
        )
    else:
        logger.error(f"Download failed: {url}")
    if cleanup_on_exception and tmpfilepath:
        try:
            os.remove(tmpfilepath)
        except (IOError, OSError) as ex:
            logger.error(f"Failed to remove temporary file: {tmpfilepath}")
            raise ex
    logger.error(str(e))
    raise e


def _download_with_wget(url: str, output_path: str) -> subprocess.CompletedProcess:
    logger.info(f"Starting download (wget): {url} ({url_to_cache_key(url)})")
    cmd = (
        "wget -x -v --continue --trust-server-names --retry-connrefused "
        "--read-timeout=60 --waitretry 60 --timeout=30 --tries 8"
    )
    cmd = cmd.split()
    cmd.extend(["-O", output_path, url])
    result = subprocess.run(cmd)
    return result


def _simple_grab_url(url: str, output_path: str):
    logger.info(f"Starting download: {url} ({url_to_cache_key(url)})")
    return urllib.request.urlretrieve(url, filename=output_path)


def download_concurrent(
    urls: Union[Sequence[str], Set[str]], cache_path, proxy=None, concurrent_downloads=8
):
    # executor = concurrent.futures.ProcessPoolExecutor
    executor = concurrent.futures.ThreadPoolExecutor
    with executor(max_workers=concurrent_downloads) as executor:
        for result in executor.map(
            download_url,  # _simple_grab_url,
            urls,
            [get_url_cached_path(url, cache_path) for url in urls],
        ):
            pass

    # for url in urls:
    #     output_path = get_url_cached_path(url, cache_path)
    #     result = _download_with_wget(url, output_path)
    #     result.check_returncode()


def init_cache(cache_path):
    """
    Create a flag file .laxydl_cache in the cache path.
    This is used as a sanity check to ensure we don't accidentally expire files in a non-cache path.

    :param cache_path: The path to the download cache to initialize.
    :type cache_path: str
    :return:
    :rtype:
    """
    if os.path.exists(cache_path) and os.path.isdir(cache_path):
        flagfile_path = os.path.join(cache_path, ".laxydl_cache")
        open(flagfile_path, "a").close()  # == touch
    else:
        logger.error(f"{cache_path} does not exist.")
        raise OSError(f"{cache_path} does not exist.")


def is_cache_path(cache_path):
    """
    Check that a flag file .laxydl_cache exists in the cache path, to ensure we aren't
    using some other non-cache path (as this may result in accidental file deletion).

    :param cache_path: The path to check.
    :type cache_path: str
    :return: True if the .laxydl_cache file exists in the cache path.
    :rtype: bool
    """
    flagfile_path = os.path.join(cache_path, ".laxydl_cache")
    return os.path.exists(flagfile_path) and os.path.isfile(flagfile_path)


def clean_cache(cache_path, cache_age: int = 30):
    """
    Delete files older than cache_age days from cache_path.

    :param cache_path: Path to the cache.
    :type cache_path: str
    :param cache_age: Remove files older this this, in days (mtime).
    :type cache_age: int
    :return:
    :rtype:
    """
    cmd = [
        "find",
        cache_path,
        "-type",
        "f",
        "-mtime",
        f"+{cache_age}",
        "-not",  # this part ignores .hidden files and dirs
        "-name",
        "\.*",
        "-print",
        "-delete",
    ]
    logger.info("Cleaning cache - running: %s" % " ".join(cmd).replace("\.*", '"\.*"'))
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


async def trio_wait_with_progress(delay, progress_every, finish_char="\n", quiet=False):
    slice = delay / progress_every
    for i in range(int(slice)):
        if not quiet:
            sys.stderr.write(".")
            sys.stderr.flush()
        await trio.sleep(progress_every)
    if not quiet:
        sys.stderr.write(finish_char)


def parse_pipeline_config(config_fh):
    config = json.loads(config_fh.read())
    config_fh.close()
    return config


def get_urls_from_pipeline_config_deprecated_sample_cart(
    config: Union[dict, OrderedDict],
    required_type_tags: Union[Iterable[str], None] = None,
) -> Dict[str, str]:
    """
    Parse deprecated fields sample_cart and sample_set from pipeline_config.json.

    {"sample_cart": {
        "id": "1Dgwk9O1TxYooCl3i7dSXo",
        "name": "Sample set created on 2020-08-04T11:00:44.896515",
        "owner": "3zJrsOmUOqpTxNNou8LkNq",
        "samples": [
            {"name": "sampleA",
            "files":
            [
                {
                "R1": {
                    "name": "sampleA_R1.fastq.gz",
                    "checksum": "md5:b0cb55825c9cec7ad32e4ec82b2524f7",
                    "location": "ftp://ftp.example.com/sampleA_R1.fastq.gz",
                    "type_tags": ["ena"],
                    "sanitized_filename": "sampleA_R1.fastq.gz"},
                "R2": {
                    "name": "sampleA_R2.fastq.gz",
                    "checksum": "md5:a0cb77825c9cec7ad32e4ec82b25df24f7",
                    "location": "ftp://ftp.example.com/sampleA_R2.fastq.gz",
                    "type_tags": ["ena"],
                    "sanitized_filename": "sampleA_R2.fastq.gz"}
                }
            ]
            }
        ]
        }
    }
    """

    url_filename_mapping = dict()
    samples = (config.get("sample_cart", {}) or {}).get("samples", [])
    if not samples:
        samples = config.get("sample_set", {}).get("samples", [])

    for sample in samples:
        for f in sample["files"]:
            for read_number, url_descriptor in f.items():
                if isinstance(url_descriptor, str):
                    url = url_descriptor
                    sanitized_filename = None
                elif isinstance(url_descriptor, dict) and url_descriptor.get(
                    "location", False
                ):
                    url = url_descriptor["location"]
                    sanitized_filename = url_descriptor.get("sanitized_filename", None)
                else:
                    continue

                if required_type_tags is None:
                    url_filename_mapping[url] = sanitized_filename
                else:
                    if isinstance(url_descriptor, dict) and set(
                        required_type_tags
                    ).issubset(set(url_descriptor.get("type_tags", []))):
                        url_filename_mapping[url] = sanitized_filename
                    elif isinstance(url_descriptor, str):
                        # If url_descriptor is a string, we can't check type_tags
                        # You might want to decide how to handle this case
                        url_filename_mapping[url] = sanitized_filename

    return url_filename_mapping


def get_urls_from_pipeline_config(
    config: Union[dict, OrderedDict],
    required_type_tags: Union[Iterable[str], None] = None,
) -> Dict[str, str]:
    """
    {"params": {
         "fetch_files": [
             {
                "name": "some_file.fasta",
                "location": "ftp://ftp.example.com/some_file.fasta",
                "type_tags": ["genome_sequence", "fasta"]
             },
             {
                "name": "some_annot.gff3",
                "location": "ftp://ftp.example.com/some_file.gff3",
                "type_tags": ["genome_annotation", "gff"]
             },
             {
                "name": "sampleA_R1.fastq.gz",
                "checksum": "md5:b0cb55825c9cec7ad32e4ec82b2524f7",
                "location": "ftp://ftp.example.com/sampleA_R1.fastq.gz",
                "metadata": {"read_pair": "R1",
                             "paired_file": "sampleA_R2.fastq.gz"},
                "type_tags": ["ena"]
            },
            {
                "name": "sampleA_R2.fastq.gz",
                "checksum": "md5:b0cb55825c9cec7ad32e4ec82b2524f7",
                "location": "ftp://ftp.example.com/sampleA_R2.fastq.gz",
                "metadata": {"read_pair": "R2",
                             "paired_file": "sampleA_R1.fastq.gz"},
                "type_tags": ["ena"]
            },
        ]
        }
    }
    """
    url_filename_mapping = dict()
    files = config.get("params", {}).get("fetch_files", [])

    if files:
        for f in files:
            fname = f.get("sanitized_filename", None)
            if fname is None:
                fname = sanitize_filename(f["name"])

            if required_type_tags is None:
                url_filename_mapping[f["location"]] = fname
            else:
                if set(required_type_tags).issubset(set(f.get("type_tags", []))):
                    url_filename_mapping[f["location"]] = fname

    # TODO: Remove the deprecated sample_set and sample_cart alternatives in the future
    else:
        url_filename_mapping = get_urls_from_pipeline_config_deprecated_sample_cart(
            config, required_type_tags=required_type_tags
        )

    return url_filename_mapping


#
# TODO: Duplicated code with laxy_backend.util - merge into single shared library
#
def sanitize_filename(
    filename: str,
    valid_filename_chars: str = None,
    replace: dict = None,
    max_length: int = 255,
    unicode_to_ascii=True,
    unquote_urlencoding=True,
) -> str:
    """
    Adapted from: https://gist.github.com/wassname/1393c4a57cfcbf03641dbc31886123b8

    Replaces or removes characters that aren't filename safe on most platforms (or often
    cause issues in shell commmands when left unescaped), spaces to underscores,
    truncates the filename length and replaces a subset of Unicode characters with
    US-ASCII transliterations (eg à -> a, 蛇 -> She).
    """
    if valid_filename_chars is None:
        # valid_filename_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        # Brackets often cause issue with improperly escaped shell commands, so we disallow those too ..
        valid_filename_chars = "-_. %s%s" % (string.ascii_letters, string.digits)

    if replace is None:
        replace = {r"\s+": "_"}

    if unquote_urlencoding:
        filename = unquote(filename)

    if unicode_to_ascii:
        filename = unidecode(filename)

    # replace spaces or other characters in the replacement dict
    for old, new in replace.items():
        filename = re.sub(old, new, filename)

    # keep only valid ascii chars
    cleaned_filename = (
        unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode()
    )

    # keep only valid chars
    cleaned_filename = "".join(c for c in cleaned_filename if c in valid_filename_chars)

    return cleaned_filename[:max_length]


#
# TODO: Duplicated code with laxy_backend.util - merge into single shared library
#
@functools.lru_cache(maxsize=1024)
def find_filename_and_size_from_url(url, sanitize_name=True, **kwargs):
    """
    Tries to determine the filename for a given download URL via the
    Content-Disposition header - falls back to path splitting if that header
    isn't present, and raises a ValueError if it can't be determined
    via path splitting.

    Supports http://, https://, ftp://, sftp:// and file:// schemes.

    Keyword args are passed directly to requests.head, so custom authentication
    or headers can be set (eg headers={'Authorization': 'Bearer blafoo'})

    :param url: The URL
    :type url: str
    :return: The download filename
    :rtype: str
    """
    scheme = urlparse(url).scheme.lower()
    file_size = None
    filename = None
    if scheme in ["http", "https"]:
        head = requests.head(url, **kwargs)
        filename_header = cgi.parse_header(head.headers.get("Content-Disposition", ""))[
            -1
        ]
        file_size = head.headers.get("Content-Length", None)
        if file_size is not None:
            file_size = int(file_size)
        if "filename" in filename_header:
            filename = filename_header.get("filename").strip()
        else:
            filename = os.path.basename(urlparse(url).path).strip()
    elif scheme == "file" or scheme == "ftp" or scheme == "sftp":
        filename = os.path.basename(urlparse(url).path).strip()

    if scheme == "file":
        file_size = os.path.getsize(urlparse(url).path)

    if not filename:
        raise ValueError("Could not find a filename for: %s" % url)

    filename = filename.strip()

    if sanitize_name:
        filename = sanitize_filename(filename)

    return filename, file_size


def _random_chars(n: int) -> str:
    return "".join([random.choice(string.ascii_letters) for i in range(n)])


def random_prefix_filename_if_exists(filepath: Union[str, Path]) -> str:
    tries = 0
    while tries < 5 and os.path.exists(filepath):
        filename = Path(filepath).name
        prefixed_filename = f"{_random_chars(4)}_{filename}"
        filepath = Path(Path(filepath).parent, prefixed_filename)
        tries += 1
    return str(filepath)


def create_symlink_to_cache(
    url: str,
    target_dir,
    cache_path,
    filename=None,
    sanitize_name=True,
):
    # Attempt to determine the filename based on the URL
    if filename is None:
        filename, _ = find_filename_and_size_from_url(url, sanitize_name=sanitize_name)

    cached = get_url_cached_path(url, cache_path)
    filepath = os.path.join(target_dir, filename)

    os.symlink(cached, filepath)


def create_copy_from_cache(
    url: str,
    target_dir,
    cache_path,
    filename=None,
    sanitize_name=True,
):
    # Attempt to determine the filename based on the URL
    if filename is None:
        filename, _ = find_filename_and_size_from_url(url, sanitize_name=sanitize_name)

    cached = get_url_cached_path(url, cache_path=cache_path)
    filepath = os.path.join(target_dir, filename)

    shutil.copyfile(cached, filepath)


def is_zipfile(fpath: str) -> bool:
    return magic.from_file(fpath, mime=True) == "application/zip"


def is_tarfile(fpath: str) -> bool:
    return tarfile.is_tarfile(fpath)


def untar(cached, target_dir, extract_files: Union[List[str], None] = None):
    if extract_files is None:
        extract_files = []

    if is_tarfile(cached):
        cmd = ["tar", "xvf", cached, "-C", target_dir]
        cmd.extend(extract_files)
        result = subprocess.run(cmd)
        result.check_returncode()
    else:
        raise ValueError(f"{cached} is not a tar file")

    return result


def unzip(cached, target_dir, extract_files: Union[List[str], None] = None):
    if extract_files is None:
        extract_files = []

    if is_zipfile(cached):
        cmd = ["unzip", "-n", "-d", target_dir, cached]
        cmd.extend(extract_files)
        result = subprocess.run(cmd)
        result.check_returncode()
    else:
        raise ValueError(f"{cached} is not a zip file")

    return result


def recursively_sanitize_filenames(
    rootpath: Union[str, Path],
    fix_root=True,
    sanitizer: Union[None, Callable] = None,
) -> List[Tuple[str, str]]:
    """[summary]
    Recursively renames files and directories to remove spaces.

    Args:
        rootpath (Union[str, Path]): Path to recursively fix.
        fix_root (bool): Also fix the rootpath name (defaults to True).
        sanitizer (Callable): (Optional) A function that takes a string and returns a sanitized version.
                              Defaults to :func:`sanitize_filename`.

    Returns:
        List[Tuple[str, str]]: A list of tuples containing the old and new path names.
    """
    if sanitizer is None:
        sanitizer = sanitize_filename

    rootpath = Path(rootpath)
    changes = []
    for root, dirs, files in reversed(list(os.walk(str(rootpath)))):
        entries = files + dirs
        for e in entries:
            oldpath = Path(root, e)
            newpath = Path(root, sanitizer(e))
            if newpath != oldpath:
                logger.info(f"Renaming {e} to {sanitizer(e)}")
                os.rename(oldpath, newpath)
                changes.append((str(oldpath), str(newpath)))

    if fix_root:
        newpath = rootpath.parent / Path(sanitizer(rootpath.name))
        if newpath != rootpath:
            logger.info(f"Renaming destination path directory {rootpath} to {newpath}")
            os.rename(rootpath, newpath)
            changes.append((str(rootpath), str(newpath)))

    return changes


def is_tar_url_with_fragment(url: str, extensions: Union[List[str], None] = None):
    if extensions is None:
        extensions = [".tar"]

    if "#" in url:
        tar_fn = Path(urlparse(url).path).name
        for ext in extensions:
            if tar_fn.endswith(ext) and urlparse(url).fragment:
                return True

    return False


def remove_url_fragment(url):
    """
    >>> remove_url_fragment("https://example.com/dir/thefile.tar#internal.txt")
    'https://example.com/dir/thefile.tar'

    :param url: A URL, possibly with a #fragment at the end
    :type url: str
    :return: The URL without the #fragment.
    :rtype: str
    """
    urlparts = list(urlsplit(url))
    urlparts[4] = ""  # remove hash fragment
    return urlunsplit(urlparts)


def untar_from_url_fragment(cached, target_dir, url: str):
    fn = urlparse(url).fragment
    return untar(cached, target_dir, extract_files=[fn])


async def async_notify_event(
    api_url: Union[str, None],
    event: str,
    message: str = "",
    extra: Union[Mapping, None] = None,
    auth_headers: Union[Mapping, None] = None,
    verify_ssl_certificate: bool = True,
):
    if api_url is None:
        return
    if extra is None:
        extra = {}
    if auth_headers is None:
        auth_headers = {}
    headers = merge_dicts({"Content-Type": "application/json"}, auth_headers)
    data = {"event": event, "message": message, "extra": extra}
    try:
        resp = await asks.post(
            api_url, json=data, headers=headers, retries=3, timeout=30
        )
        return resp
    except ssl.SSLError as ex:
        # asks doesn't yet support a (simple) way to ignore self-signed ssl certs, so we just fallback
        # to the synchronous option in this case.
        if not verify_ssl_certificate:
            logger.warning(f"SSL CERTIFICATE_VERIFY_FAILED: {api_url}")
            return notify_event(
                api_url,
                message=message,
                json=data,
                headers=headers,
                retries=3,
                timeout=30,
                verify=verify_ssl_certificate,
            )
        else:
            logger.exception(ex)
    except BaseException as ex:
        logger.exception(ex)


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, urllib.error.URLError),
    max_tries=3,
    jitter=backoff.full_jitter,
    on_giveup=lambda e: logger.debug(
        f"Event notification failed: {e.get('event', '')}"
    ),
)
def notify_event(
    api_url: Union[str, None],
    event: str,
    message: str = "",
    extra: Union[Mapping, None] = None,
    auth_headers: Union[Mapping, None] = None,
    verify_ssl_certificate: bool = True,
):
    if api_url is None:
        return
    if extra is None:
        extra = {}
    if auth_headers is None:
        auth_headers = {}
    headers = merge_dicts({"Content-Type": "application/json"}, auth_headers)
    data = {"event": event, "message": message, "extra": extra}
    try:
        resp = requests.post(
            api_url,
            json=data,
            headers=headers,
            timeout=30,
            verify=verify_ssl_certificate,
        )
        return resp
    except requests.exceptions.SSLError as ex:
        logger.exception(ex)
