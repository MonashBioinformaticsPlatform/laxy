#!/usr/bin/env python3
from email.message import EmailMessage as HTTPHeaders
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

try:
    from urllib3.exceptions import ProtocolError as Urllib3ProtocolError
except ImportError:  # pragma: no cover
    Urllib3ProtocolError = ()  # type: ignore

logger = logging.getLogger(__name__)
# logging.basicConfig(format='%(levelname)s: %(asctime)s -- %(message)s', level=logging.INFO)

asks.init(trio)

HTTP_TIMEOUT = (30, 120)  # connect, read between chunks
RETRY_WAIT_INITIAL = 15.0
RETRY_WAIT_CAP = 300.0  # 5 minutes
DEFAULT_MAX_ATTEMPTS = 50
DEFAULT_NO_PROGRESS_ATTEMPTS = 10
ARIA_MAX_ROUNDS = 6
ARIA_PERMANENT_ERROR_CODES = frozenset({"3", "9", "24"})
# 408/416/429 are retried; every other 4xx is permanent.
TRANSIENT_HTTP_CLIENT_ERRORS = frozenset({408, 416, 429})

_TRANSIENT_STREAM_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.Timeout,
)
if Urllib3ProtocolError:
    _TRANSIENT_STREAM_ERRORS = _TRANSIENT_STREAM_ERRORS + (Urllib3ProtocolError,)

_CONTENT_RANGE_RE = re.compile(
    r"bytes\s+(?P<start>\d+)-(?P<end>\d+)/(?P<total>\d+|\*)",
    re.IGNORECASE,
)


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
    e.message = f"Request failed ({response.status_code}) {response.reason} : {response.url}"
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
        # Transient statuses trigger retries (via the backoff decorator):
        # 429 Too Many Requests is what CDNs (e.g. jsDelivr) return under load,
        # and 502/503/504 are common when a reverse-proxied web app behind
        # Nginx/Apache is temporarily restarting or overloaded.
        if response.status_code in (429, 500, 502, 503, 504):
            _raise_request_exception(response)

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None:
            logger.error(
                f"Request failed ({e.response.status_code}) {e.response.reason} : {e.response.url}"
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


def parse_optional_int(value) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_content_range(
    header: Optional[str],
) -> Optional[Tuple[int, int, Optional[int]]]:
    if not header:
        return None
    match = _CONTENT_RANGE_RE.search(header)
    if not match:
        return None
    total_raw = match.group("total")
    total = None if total_raw == "*" else int(total_raw)
    return int(match.group("start")), int(match.group("end")), total


def expected_size_from_http_response(response) -> Optional[int]:
    headers = getattr(response, "headers", {}) or {}
    status = getattr(response, "status_code", None)
    if status == 206:
        parsed = parse_content_range(
            headers.get("Content-Range") or headers.get("content-range")
        )
        if parsed is not None:
            return parsed[2]
        return None
    return parse_optional_int(
        headers.get("Content-Length") or headers.get("content-length")
    )


def content_range_start(response) -> Optional[int]:
    headers = getattr(response, "headers", {}) or {}
    parsed = parse_content_range(
        headers.get("Content-Range") or headers.get("content-range")
    )
    if parsed is None:
        return None
    return parsed[0]


def is_permanent_http_status(status_code: Optional[int]) -> bool:
    if status_code is None:
        return False
    return 400 <= status_code < 500 and status_code not in TRANSIENT_HTTP_CLIENT_ERRORS


def is_transient_http_status(status_code: Optional[int]) -> bool:
    if status_code is None:
        return False
    if status_code in TRANSIENT_HTTP_CLIENT_ERRORS:
        return True
    return status_code >= 500


def retry_wait_seconds(
    attempt: int,
    initial: float = RETRY_WAIT_INITIAL,
    cap: float = RETRY_WAIT_CAP,
) -> float:
    expo = initial * (2 ** attempt)
    return backoff.full_jitter(min(cap, expo))


def sleep_before_retry(attempt: int) -> None:
    delay = retry_wait_seconds(attempt)
    logger.info(f"Waiting {delay:.1f}s before retry (attempt {attempt + 1})")
    time.sleep(delay)


def decide_existing_download(
    *,
    skip_existing: bool,
    destination_exists: bool,
    destination_is_symlink: bool,
    destination_size: Optional[int],
    cache_exists: bool,
    cache_size: Optional[int],
    aria2_control_exists: bool,
    content_length: Optional[int],
) -> str:
    """
    Decide what to do with an existing destination / cache file.

    Returns one of: skip, resume, copy_dest_to_cache, replace_cache, download.
    """
    oversized_cache = (
        cache_exists
        and content_length is not None
        and cache_size is not None
        and cache_size > content_length
    )
    if oversized_cache:
        return "replace_cache"

    unfinished_cache = aria2_control_exists or (
        cache_exists
        and content_length is not None
        and cache_size is not None
        and cache_size < content_length
    )
    if unfinished_cache:
        return "resume"

    if skip_existing and destination_exists:
        if cache_exists:
            return "skip"
        if content_length is None:
            return "skip"
        if destination_size == content_length:
            return "skip"
        if destination_size is not None and destination_size < content_length:
            if destination_is_symlink:
                return "resume"
            return "copy_dest_to_cache"
        if destination_size is not None and destination_size > content_length:
            return "replace_cache"
        return "skip"

    return "download"


def inspect_existing_download(
    *,
    skip_existing: bool,
    destination_path: Optional[str],
    cache_file: Optional[str],
    content_length: Optional[int],
) -> str:
    dest_exists = bool(
        destination_path
        and os.path.lexists(destination_path)
        and (os.path.isfile(destination_path) or os.path.islink(destination_path))
    )
    dest_is_symlink = bool(destination_path and os.path.islink(destination_path))
    dest_size = None
    if dest_exists and destination_path and os.path.isfile(destination_path):
        dest_size = os.path.getsize(destination_path)
    cache_exists = bool(cache_file and os.path.isfile(cache_file))
    cache_size = os.path.getsize(cache_file) if cache_exists else None
    aria2_control = bool(cache_file and os.path.isfile(f"{cache_file}.aria2"))
    return decide_existing_download(
        skip_existing=skip_existing,
        destination_exists=dest_exists,
        destination_is_symlink=dest_is_symlink,
        destination_size=dest_size,
        cache_exists=cache_exists,
        cache_size=cache_size,
        aria2_control_exists=aria2_control,
        content_length=content_length,
    )


def apply_existing_download_decision(
    decision: str,
    *,
    destination_path: Optional[str],
    cache_file: Optional[str],
) -> None:
    def _remove(path: Optional[str]) -> None:
        if path and os.path.lexists(path):
            os.remove(path)

    if decision == "skip":
        return
    if decision == "copy_dest_to_cache":
        if not destination_path or not cache_file:
            return
        os.makedirs(os.path.dirname(cache_file) or ".", exist_ok=True)
        shutil.copy2(destination_path, cache_file)
        _remove(destination_path)
        return
    if decision == "replace_cache":
        _remove(cache_file)
        if cache_file:
            _remove(f"{cache_file}.aria2")
        _remove(destination_path)
        return
    if decision == "resume":
        _remove(destination_path)
        return


def classify_aria_round(
    items: Sequence[Mapping],
    round_index: int,
    max_rounds: int = ARIA_MAX_ROUNDS,
) -> Dict[str, Union[List[str], bool]]:
    """
    Classify aria2 statuses after a round.

    Each item is a mapping with keys:
      url, status, errorCode, cache_size, content_length
    """
    ok: List[str] = []
    requeue: List[str] = []
    failed: List[str] = []
    last_round = round_index >= max_rounds - 1

    for item in items:
        url = str(item.get("url", ""))
        status = item.get("status")
        error_code = str(item.get("errorCode") or "")
        cache_size = parse_optional_int(item.get("cache_size"))
        content_length = parse_optional_int(item.get("content_length"))

        if status == "complete":
            if (
                content_length is not None
                and cache_size is not None
                and cache_size != content_length
            ):
                decision = "requeue"
            else:
                decision = "ok"
        elif status in ("error", "removed"):
            if error_code in ARIA_PERMANENT_ERROR_CODES:
                decision = "failed"
            else:
                decision = "requeue"
        else:
            decision = "requeue"

        if decision == "requeue" and last_round:
            decision = "failed"

        if decision == "ok":
            ok.append(url)
        elif decision == "failed":
            failed.append(url)
        else:
            requeue.append(url)

    return {
        "ok": ok,
        "requeue": requeue,
        "failed": failed,
        "exhausted": last_round and bool(failed or requeue),
    }


class _RetryDownload(Exception):
    """Internal signal to discard a partial and retry the current download."""


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
    max_retries: int = DEFAULT_MAX_ATTEMPTS,
    no_progress_max: int = DEFAULT_NO_PROGRESS_ATTEMPTS,
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
        remove_existing (bool): Whether to remove an existing file if it is larger than the expected size.
        chunk_size (int): The size of chunks to use when streaming the download.
        max_retries (int): Hard cap on the number of download attempts.
        no_progress_max (int): Consecutive attempts that add no bytes before giving up.

    Returns:
        str: The path to the downloaded file.

    Raises:
        Exception: If the download fails or if the downloaded file is incomplete.
    """
    auth = None
    if username is not None and password is not None:
        auth = HTTPBasicAuth(username, password)

    headers = headers or {}
    # requests/urllib3 transparently decompresses gzip/br transfer encoding,
    # so the bytes written to disk would be the *decompressed* size while
    # Content-Length reflects the *compressed* size on the wire - the two
    # never match for any server that compresses its responses (eg jsDelivr).
    # Requesting identity encoding keeps Content-Length comparable to what we
    # actually write, so the size-verification below is meaningful.
    headers.setdefault("Accept-Encoding", "identity")
    filepath = Path(filepath)
    directory = tmp_directory or str(filepath.parent)
    filename = filepath.name
    filepath = str(filepath)
    scheme = urlparse(url).scheme.lower()

    lock_path = f"{filepath}.lock"
    lock = FileLock(lock_path, timeout=60 * 60 * 12)  # 12 hours timeout
    tmpfile_path = None

    def _save_partial(src: Optional[str]) -> None:
        if src and os.path.exists(src):
            shutil.move(src, filepath)

    def _discard_partial() -> None:
        if os.path.exists(filepath):
            os.remove(filepath)

    try:
        with lock:
            content_length = parse_optional_int(
                get_content_length(url, headers, auth, scheme)
            )

            if check_existing_size and os.path.exists(filepath):
                existing_size = os.path.getsize(filepath)
                if content_length is not None and existing_size == content_length:
                    logger.info(
                        f"File of correct size {filepath} ({content_length} bytes) already exists, skipping download"
                    )
                    return filepath
                elif (
                    remove_existing
                    and content_length is not None
                    and existing_size > content_length
                ):
                    logger.info(
                        f"File exists {filepath} but is larger than Content-Length "
                        f"({existing_size} > {content_length} bytes). Deleting existing file."
                    )
                    os.remove(filepath)
                elif content_length is not None and existing_size < content_length:
                    logger.info(
                        f"File exists {filepath} but is shorter than Content-Length "
                        f"({existing_size} < {content_length} bytes). Will resume."
                    )

            no_progress_count = 0
            last_error: Optional[BaseException] = None

            for attempt in range(max_retries):
                logger.info(
                    f"Starting download (attempt {attempt + 1}/{max_retries}): {url} ({url_to_cache_key(url)})"
                )

                size_before = (
                    os.path.getsize(filepath) if os.path.exists(filepath) else 0
                )
                partial_size = size_before if size_before > 0 else None
                expected_size = content_length
                retry_now = False

                with temporary_file(
                    mode="wb", dir=directory, prefix=f"{filename}.", suffix=".tmp"
                ) as tmpfile:
                    tmpfile_path = tmpfile.name
                    if partial_size is not None:
                        shutil.copy2(filepath, tmpfile.name)

                    try:
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
                                    timeout=HTTP_TIMEOUT,
                                )
                            ) as download:
                                download.raise_for_status()

                                if expected_size is None:
                                    expected_size = expected_size_from_http_response(
                                        download
                                    )

                                if (
                                    partial_size
                                    and download.status_code == 206
                                    and content_range_start(download) is not None
                                    and content_range_start(download) != partial_size
                                ):
                                    logger.warning(
                                        f"Content-Range start for {url} is "
                                        f"{content_range_start(download)}, expected "
                                        f"{partial_size}; discarding local file and retrying."
                                    )
                                    raise _RetryDownload()

                                if partial_size and download.status_code == 200:
                                    mode = "wb"
                                else:
                                    mode = "ab" if partial_size else "wb"

                                with open(tmpfile.name, mode) as f:
                                    try:
                                        for chunk in download.iter_content(
                                            chunk_size=chunk_size
                                        ):
                                            f.write(chunk)
                                        f.flush()
                                        os.fsync(f.fileno())
                                    except _TRANSIENT_STREAM_ERRORS:
                                        f.flush()
                                        os.fsync(f.fileno())
                                        raise
                    except requests.exceptions.HTTPError as e:
                        status_code = (
                            e.response.status_code
                            if e.response is not None
                            else None
                        )
                        if (
                            status_code == 416
                            and partial_size
                            and attempt < max_retries - 1
                        ):
                            logger.warning(
                                f"Range request for {url} got 416 Range Not "
                                f"Satisfiable (local size {partial_size}); "
                                "discarding local file and retrying with a "
                                "full download."
                            )
                            _discard_partial()
                            if tmpfile_path and os.path.exists(tmpfile_path):
                                os.remove(tmpfile_path)
                            tmpfile_path = None
                            last_error = e
                            sleep_before_retry(attempt)
                            continue
                        if is_permanent_http_status(status_code):
                            raise
                        if is_transient_http_status(status_code):
                            logger.warning(
                                f"Transient HTTP {status_code} downloading {url}; "
                                "keeping partial and retrying."
                            )
                            _save_partial(tmpfile_path)
                            tmpfile_path = None
                            last_error = e
                            retry_now = True
                        else:
                            raise
                    except _TRANSIENT_STREAM_ERRORS as e:
                        logger.warning(
                            f"Connection dropped while downloading {url}: {e}. "
                            "Keeping partial and retrying."
                        )
                        _save_partial(tmpfile_path)
                        tmpfile_path = None
                        last_error = e
                        retry_now = True
                    except urllib.error.URLError as e:
                        logger.warning(
                            f"URL error while downloading {url}: {e}. "
                            "Keeping partial and retrying."
                        )
                        _save_partial(tmpfile_path)
                        tmpfile_path = None
                        last_error = e
                        retry_now = True
                    except requests.exceptions.RequestException as e:
                        status_code = (
                            e.response.status_code
                            if getattr(e, "response", None) is not None
                            else None
                        )
                        if is_permanent_http_status(status_code):
                            raise
                        logger.warning(
                            f"Request failed while downloading {url}: {e}. "
                            "Keeping partial and retrying."
                        )
                        _save_partial(tmpfile_path)
                        tmpfile_path = None
                        last_error = e
                        retry_now = True
                    except _RetryDownload:
                        _discard_partial()
                        if tmpfile_path and os.path.exists(tmpfile_path):
                            os.remove(tmpfile_path)
                        tmpfile_path = None
                        last_error = None
                        retry_now = True

                    if retry_now:
                        size_after = (
                            os.path.getsize(filepath)
                            if os.path.exists(filepath)
                            else 0
                        )
                        if size_after > size_before:
                            no_progress_count = 0
                        else:
                            no_progress_count += 1
                        if no_progress_count >= no_progress_max:
                            raise Exception(
                                f"Download of {url} made no progress in "
                                f"{no_progress_count} consecutive attempts."
                            )
                        if attempt < max_retries - 1:
                            sleep_before_retry(attempt)
                            continue
                        if last_error:
                            raise last_error
                        raise Exception(
                            f"Download of {url} failed after {max_retries} attempts."
                        )

                    if not os.path.exists(tmpfile_path):
                        continue

                    file_size = os.path.getsize(tmpfile_path)
                    if expected_size is None or file_size == expected_size:
                        shutil.move(tmpfile_path, filepath)
                        tmpfile_path = None
                        return filepath

                    shutil.move(tmpfile_path, filepath)
                    tmpfile_path = None
                    logger.warning(
                        f"Downloaded file size ({file_size}) does not match "
                        f"Content-Length ({expected_size}). Retrying..."
                    )
                    if file_size > size_before:
                        no_progress_count = 0
                    else:
                        no_progress_count += 1
                    if no_progress_count >= no_progress_max:
                        raise Exception(
                            f"Downloaded file size ({file_size}) does not match "
                            f"Content-Length ({expected_size}) after "
                            f"{no_progress_count} consecutive attempts with no progress."
                        )
                    if attempt < max_retries - 1:
                        sleep_before_retry(attempt)
                    else:
                        raise Exception(
                            f"Downloaded file size ({file_size}) does not match "
                            f"Content-Length ({expected_size}) after {max_retries} attempts."
                        )

            raise Exception(
                f"Download of {url} failed after {max_retries} attempts."
            )

    except Exception as e:
        handle_download_exception(
            e, getattr(e, "status_code", None), url, cleanup_on_exception, tmpfile_path
        )
        raise
    finally:
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
            if not head_request.ok:
                # Some dynamic endpoints (eg NCBI eutils efetch.fcgi) don't
                # support HEAD and return a small error body (405, etc) with
                # its own unrelated Content-Length - trusting that would make
                # a perfectly good GET download look corrupt.
                logger.warning(
                    f"HEAD request to {url} returned {head_request.status_code}, "
                    "cannot use its Content-Length to verify download size."
                )
                return None
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
            logger.warning(f"Failed to remove temporary file: {tmpfilepath}")
            # Don't re-raise the cleanup exception, just log it
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
        ".*",
        "-print",
        "-delete",
    ]
    logger.info("Cleaning cache - running: %s", " ".join(cmd))
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
            # f is a dict like {"R1": ..., "type_tags": [...], ...}
            # We want to check type_tags at the file level if present
            type_tags = f.get("type_tags", [])
            for read_number, url_descriptor in f.items():
                if read_number == "type_tags":
                    continue
                if isinstance(url_descriptor, str):
                    url = url_descriptor
                    sanitized_filename = None
                    # Use file-level type_tags if present
                    tags_to_check = type_tags
                elif isinstance(url_descriptor, dict) and url_descriptor.get(
                    "location", False
                ):
                    url = url_descriptor["location"]
                    sanitized_filename = url_descriptor.get("sanitized_filename", None)
                    tags_to_check = url_descriptor.get("type_tags", type_tags)
                else:
                    continue

                if required_type_tags is None:
                    url_filename_mapping[url] = sanitized_filename
                else:
                    if set(required_type_tags).issubset(set(tags_to_check)):
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
        # Only return URLs that matched the required_type_tags
        return url_filename_mapping
    else:
        # Deprecated format
        return get_urls_from_pipeline_config_deprecated_sample_cart(
            config, required_type_tags=required_type_tags
        )


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
        valid_filename_chars = f"-_. {string.ascii_letters}{string.digits}"

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
        content_disposition = head.headers.get("Content-Disposition", "")
        if content_disposition:
            msg = HTTPHeaders()
            msg['Content-Disposition'] = content_disposition
            filename = msg.get_param('filename', header='Content-Disposition')
            if filename:
                filename = filename.strip()
        else:
            filename = None
        file_size = head.headers.get("Content-Length", None)
        if file_size is not None:
            file_size = int(file_size)
        if not filename:
            filename = os.path.basename(urlparse(url).path).strip()
    elif scheme == "file" or scheme == "ftp" or scheme == "sftp":
        filename = os.path.basename(urlparse(url).path).strip()

    if scheme == "file":
        file_size = os.path.getsize(urlparse(url).path)

    if not filename:
        raise ValueError(f"Could not find a filename for: {url}")

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
