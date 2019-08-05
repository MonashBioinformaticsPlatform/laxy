#!/usr/bin/env python3
import cgi
import json
import ssl
import urllib
from contextlib import closing
from urllib.parse import urlparse, urlsplit, urlunsplit
from pathlib import Path
import shutil
from typing import List, Union, Mapping
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

import requests
import backoff
from toolz.dicttoolz import merge as merge_dicts
from requests.auth import HTTPBasicAuth
import magic
import trio
import asks
from attrdict import AttrDict

logger = logging.getLogger(__name__)
# logging.basicConfig(format='%(levelname)s: %(asctime)s -- %(message)s', level=logging.INFO)

asks.init(trio)


def get_tmpdir():
    return '/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()


def get_default_cache_path():
    return os.path.join(get_tmpdir(), 'laxy_downloader_cache')


def url_to_cache_key(url):
    if is_tar_url_with_fragment(url):
        url = remove_url_fragment(url)

    base64ed = urlsafe_b64encode(url.encode('utf-8')).decode('ascii')
    return base64ed


def get_url_cached_path(url, cache_path):
    return os.path.join(cache_path, url_to_cache_key(url))


def _raise_request_exception(response):
    e = requests.exceptions.RequestException(response=response)
    e.message = "Request failed (%s) %s : %s" % (response.status_code,
                                                 response.reason,
                                                 response.url)
    raise e


@backoff.on_exception(backoff.expo,
                      (requests.exceptions.RequestException,
                       urllib.error.URLError),
                      max_tries=8,
                      jitter=backoff.full_jitter)
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
    if scheme in ['ftp', 'ftps', 'data']:
        return urllib.request.urlopen(url)

    # headers = copy(global_headers)
    headers = {}
    extra_headers = kwargs.get('headers', None)
    if extra_headers:
        kwargs['headers'] = merge_dicts(headers, extra_headers)

    try:
        response = requests.request(*args, **kwargs)
        # 502 Bad Gateway triggers retries - this is a common status
        # code when a reverse proxied web app behind Nginx or Apache is
        # temporarily restarting
        if response.status_code == 502:
            _raise_request_exception(response)

    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            logger.error("Request failed (%s) %s : %s",
                         e.response.status_code,
                         e.response.reason,
                         e.response.url)
        else:
            logger.error("Request failed : an exception occurred and the web "
                         "request was not made.")
        raise e

    return response


def download_url(url,
                 filepath,
                 headers=None,
                 username=None,
                 password=None,
                 tmp_directory=None,
                 cleanup_on_exception=True,
                 check_existing_size=True,
                 remove_existing=True,
                 chunk_size=1024):
    """

    :param chunk_size:
    :type chunk_size:
    :param tmp_directory:
    :type tmp_directory:
    :param cleanup_on_exception:
    :type cleanup_on_exception:
    :param check_existing_size:
    :type check_existing_size:
    :param remove_existing:
    :type remove_existing:
    :param url:
    :type url:
    :param filepath:
    :type filepath:
    :param headers: A dictionary of HTTP headers to use for the request.
    :type headers: dict
    :param username:
    :type username:
    :param password:
    :type password:
    :return:
    :rtype:
    """

    auth = None
    if username is not None and password is not None:
        auth = HTTPBasicAuth('user', 'pass')

    if headers is None:
        headers = {}

    filepath = Path(filepath)
    directory = tmp_directory
    if directory is None:
        directory = str(filepath.parent)

    filename = filepath.name
    filepath = str(filepath)

    scheme = urlparse(url).scheme

    # TODO: We should unify parts of the FTP vs HTTP(S) code,
    #       or at least factor out the FTP and HTTP parts here
    #       into functions
    if scheme == 'ftp':
        with tempfile.NamedTemporaryFile(mode='wb',
                                         dir=directory,
                                         prefix=f'{filename}.',
                                         suffix='.tmp',
                                         delete=False) as tmpfile:
            tmpfilepath = str(Path(directory, tmpfile.name))
            logger.info(f"Starting download: {url} ({url_to_cache_key(url)})")
            urllib.request.urlretrieve(url, filename=tmpfilepath)
            shutil.move(tmpfilepath, filepath)
            return filepath

    # We download to a temporary file then move it once
    # the download is complete
    tmpfilepath = None
    status_code = None
    try:
        logger.info(f"Starting download: {url} ({url_to_cache_key(url)})")
        with closing(request_with_retries(
                'GET', url,
                stream=True,
                headers=headers,
                auth=auth)) as download:
            content_length = int(download.headers.get('content-length', None))
            status_code = download.status_code

            # TODO: This isn't very smart caching - we don't look at
            #       HTTP cache headers, just rely on the file size and
            #       reported Content-Length alone. Content-Length might not
            #       even be returned by some servers.
            # ( https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching )
            if content_length and check_existing_size and \
                    os.path.exists(filepath):
                if os.path.getsize(filepath) == content_length:
                    logger.info("File of correct size %s (%s bytes) already "
                                "exists, skipping download" % (filepath,
                                                               content_length))
                    return filepath
                elif remove_existing:
                    logger.info("File exists %s but is incorrect size "
                                "(%s bytes). Deleting existing file." %
                                (filepath, content_length))
                    os.remove(filepath)

            with tempfile.NamedTemporaryFile(mode='wb',
                                             dir=directory,
                                             prefix=f'{filename}.',
                                             suffix='.tmp',
                                             delete=False) as tmpfile:
                tmpfilepath = str(Path(directory, tmpfile.name))
                for chunk in download.iter_content(chunk_size=chunk_size):
                    status_code = download.status_code
                    tmpfile.write(chunk)

                    # TODO: Stream this through xxhash64 or MD5 by default and
                    #       always return the checksum

            # TODO: If the stream ends prematurely, an exception isn't
            #       raised - we need to deal with this
            #       (eg, rely on expected Content-Length ?)
            #       If content_length > final file_size, we could also resume
            #       by adding a Range header (
            #        header = {'Range': 'bytes=%d-' % file_size}
            #       (and reopen tmpfilepath as mode='ab')
            file_size = os.path.getsize(tmpfilepath)
            if file_size < content_length:
                raise Exception("Downloaded file appears incomplete based on "
                                "Content-Length header.")

    except Exception as e:
        if status_code:
            logger.error("Download failed (%s %s): %s" %
                         (status_code, response_codes[status_code], url))
        else:
            logger.error("Download failed: %s" % url)
        if cleanup_on_exception and tmpfilepath:
            try:
                os.remove(tmpfilepath)
            except (IOError, OSError) as ex:
                logger.error("Failed to remove temporary file: %s" %
                             tmpfilepath)
                raise ex

        logger.error("%s" % str(e))
        raise e

    shutil.move(tmpfilepath, filepath)

    return filepath


def _download_with_wget(url: str, output_path: str) -> subprocess.CompletedProcess:
    logger.info(f'Starting download (wget): {url} ({url_to_cache_key(url)})')
    cmd = 'wget -x -v --continue --trust-server-names --retry-connrefused ' \
          '--read-timeout=60 --waitretry 60 --timeout=30 --tries 8'
    cmd = cmd.split()
    cmd.extend(['-O', output_path, url])
    result = subprocess.run(cmd)
    return result


def _simple_grab_url(url: str, output_path: str):
    logger.info(f'Starting download: {url} ({url_to_cache_key(url)})')
    return urllib.request.urlretrieve(url, filename=output_path)


def download_concurrent(urls: List[str], cache_path, proxy=None, concurrent_downloads=8):
    # executor = concurrent.futures.ProcessPoolExecutor
    executor = concurrent.futures.ThreadPoolExecutor
    with executor(max_workers=concurrent_downloads) as executor:
        for result in executor.map(download_url,  # _simple_grab_url,
                                   urls,
                                   [get_url_cached_path(url, cache_path) for url in urls]):
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
        flagfile_path = os.path.join(cache_path, '.laxydl_cache')
        open(flagfile_path, 'a').close()  # == touch
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
    flagfile_path = os.path.join(cache_path, '.laxydl_cache')
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
    cmd = ['find', cache_path,
           '-name', '".*"', '-prune', '-o',  # this part ignores .hidden files and dirs
           '-type', 'f', '-mtime', f'+{cache_age}', '-print', '-delete']
    logger.info("Cleaning cache - running: %s" % ' '.join(cmd))
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


async def trio_wait_with_progress(delay, progress_every, finish_char='\n', quiet=False):
    slice = delay / progress_every
    for i in range(int(slice)):
        if not quiet:
            sys.stderr.write('.')
            sys.stderr.flush()
        await trio.sleep(progress_every)
    if not quiet:
        sys.stderr.write(finish_char)


def parse_pipeline_config(config_fh):
    config = json.loads(config_fh.read())
    config_fh.close()
    return config


def get_urls_from_pipeline_config(config):
    urls = set()
    samples = config.get('sample_cart', {}).get('samples', [])
    # TODO: Remove the sample_set alternative in the future
    # Deprecated: old sample cart name
    if not samples:
        samples = config.get('sample_set', {}).get('samples', [])
    for sample in samples:
        for f in sample['files']:
            for read_number, url_descriptor in f.items():
                if isinstance(url_descriptor, str):
                    urls.add(url_descriptor)
                elif isinstance(url_descriptor, dict) and url_descriptor.get('location', False):
                    urls.add(url_descriptor['location'])

    return urls


@functools.lru_cache(maxsize=1024)
def find_filename_and_size_from_url(url, **kwargs):
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
    if scheme in ['http', 'https']:
        head = requests.head(url, **kwargs)
        filename_header = cgi.parse_header(
            head.headers.get('Content-Disposition', ''))[-1]
        file_size = head.headers.get('Content-Length', None)
        if file_size is not None:
            file_size = int(file_size)
        if 'filename' in filename_header:
            filename = filename_header.get('filename').strip()
        else:
            filename = os.path.basename(urlparse(url).path).strip()
    elif scheme == 'file' or scheme == 'ftp' or scheme == 'sftp':
        filename = os.path.basename(urlparse(url).path).strip()

    if scheme == 'file':
        file_size = os.path.getsize(urlparse(url).path)

    if not filename:
        raise ValueError('Could not find a filename for: %s' % url)

    return filename, file_size


def create_symlink_to_cache(url: str, target_dir, cache_path, filename=None):
    # Attempt to determine the filename based on the URL
    if filename is None:
        filename, _ = find_filename_and_size_from_url(url)

    cached = get_url_cached_path(url, cache_path)
    os.symlink(cached, os.path.join(target_dir, filename))


def create_copy_from_cache(url: str, target_dir, cache_path, filename=None):
    # Attempt to determine the filename based on the URL
    if filename is None:
        filename, _ = find_filename_and_size_from_url(url)

    cached = get_url_cached_path(url, cache_path=cache_path)
    shutil.copyfile(cached, os.path.join(target_dir, filename))


def is_zipfile(fpath: str) -> bool:
    return magic.from_file(fpath, mime=True) == 'application/zip'


def is_tarfile(fpath: str) -> bool:
    return tarfile.is_tarfile(fpath)


def untar(cached, target_dir, extract_files: Union[List[str], None] = None):
    if extract_files is None:
        extract_files = []

    if is_tarfile(cached):
        cmd = ['tar', 'xvf', cached, '-C', target_dir]
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
        cmd = ['unzip', '-n', '-d', target_dir, cached]
        cmd.extend(extract_files)
        result = subprocess.run(cmd)
        result.check_returncode()
    else:
        raise ValueError(f"{cached} is not a zip file")

    return result


def is_tar_url_with_fragment(url: str, extensions: Union[List[str], None] = None):
    if extensions is None:
        extensions = ['.tar']

    if '#' in url:
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
    urlparts[4] = ''  # remove hash fragment
    return urlunsplit(urlparts)


def untar_from_url_fragment(cached, target_dir, url: str):
    fn = urlparse(url).fragment
    return untar(cached, target_dir, extract_files=[fn])


async def async_notify_event(api_url: Union[str, None],
                             event: str,
                             message: str = '',
                             extra: Union[Mapping, None] = None,
                             auth_headers: Union[Mapping, None] = None,
                             verify_ssl_certificate: bool = True):
    if api_url is None:
        return
    if extra is None:
        extra = {}
    if auth_headers is None:
        auth_headers = {}
    headers = merge_dicts({'Content-Type': 'application/json'}, auth_headers)
    data = {'event': event, 'message': message, 'extra': extra}
    try:
        resp = await asks.post(api_url, json=data, headers=headers, retries=3, timeout=30)
        return resp
    except ssl.SSLError as ex:
        # asks doesn't yet support a (simple) way to ignore self-signed ssl certs, so we just fallback
        # to the synchronous option in this case.
        if not verify_ssl_certificate:
            logger.warning(f"SSL CERTIFICATE_VERIFY_FAILED: {api_url}")
            return notify_event(api_url, message=message, json=data, headers=headers,
                                retries=3, timeout=30, verify=verify_ssl_certificate)
        else:
            logger.exception(ex)
    except BaseException as ex:
        logger.exception(ex)


@backoff.on_exception(backoff.expo,
                      (requests.exceptions.RequestException,
                       urllib.error.URLError),
                      max_tries=3,
                      jitter=backoff.full_jitter,
                      on_giveup=lambda e: logger.debug(f"Event notification failed: {e.get('event', '')}"))
def notify_event(api_url: Union[str, None],
                 event: str,
                 message: str = '',
                 extra: Union[Mapping, None] = None,
                 auth_headers: Union[Mapping, None] = None,
                 verify_ssl_certificate: bool = True):
    if api_url is None:
        return
    if extra is None:
        extra = {}
    if auth_headers is None:
        auth_headers = {}
    headers = merge_dicts({'Content-Type': 'application/json'}, auth_headers)
    data = {'event': event, 'message': message, 'extra': extra}
    try:
        resp = requests.post(api_url, json=data, headers=headers, timeout=30, verify=verify_ssl_certificate)
        return resp
    except requests.exceptions.SSLError as ex:
        logger.exception(ex)
