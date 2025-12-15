import logging
from contextlib import closing
from pathlib import Path
from typing import List, Tuple, Pattern, Union, Dict
from collections import defaultdict
import urllib
from urllib.parse import urljoin, urlparse
import re
import os
import requests
from requests import HTTPError, Response
import magic  # python-magic
from cache_memoize import cache_memoize

from laxy_backend.tasks.download import request_with_retries

logger = logging.getLogger(__name__)


# @cache_memoize(timeout=1*60*60)
def is_archive_link(url: str, content_head: bytes = None, use_network=False) -> bool:
    """
    Attempts to determine if a given URL is a TAR file based on file extensions
    or the first 512 bytes of content. Also works on simple file paths.

    :param url: The URL of interest
    :type url: str
    :param content_head: Optional head content (not HTTP HEAD, actual body content)
    :type content_head: bytes
    :param use_network: If we can't guess from the filename or content head,
                        attempt to retrieve the first 512 bytes of the file and use
                        file magic to detect it's type.
    :type use_network:  bool
    :return: True if URL is detected as a TAR file
    :rtype: bool
    """
    def _smells_like_tar(content):
        sniffed_type = magic.from_buffer(content_head, mime=True)
        logger.debug('is_archive_link - detected MIME type: %s', sniffed_type)
        return sniffed_type.startswith('application/x-tar')

    if content_head is not None:
        assert len(content_head) >= 512
        return _smells_like_tar(content_head)

    tar_suffixes = ['.tar', '.tar.gz', '.tar.bz2']
    if any([urlparse(url).path.endswith(suffix) for suffix in tar_suffixes]):
        return True

    if use_network and content_head is None:
        content_head = get_url_filelike(url).read(512)
        return _smells_like_tar(content_head)

    return False


def get_url_streaming(url: str, headers=None, auth=None) -> Union[requests.Response, urllib.response.addinfourl]:
    scheme = urlparse(url).scheme
    if scheme == 'http' or scheme == 'https':
        headers = headers or {}
        response = request_with_retries(
            'GET', url,
            stream=True,
            headers=headers,
            auth=auth)
        response.raise_for_status()
        response.raw.decode_content = True
        return response
    elif scheme == 'ftp':
        if auth and '@' not in urlparse(url).netloc:
            user, pw = auth['username'], auth['password']
            url = url.replace('ftp://', f'ftp://{user}:{pw}@')
        return urllib.request.urlopen(url)


def get_url_filelike(url: str, headers=None, auth=None):
    """
    Returns a streaming file-like (something that minimally allows 'read(bytes)') from an HTTP(S) or FTP URL.

    :param url:
    :type url:
    :param headers:
    :type headers:
    :param auth:
    :type auth:
    :return:
    :rtype:
    """
    resp = get_url_streaming(url, headers=headers, auth=auth)
    if isinstance(resp, requests.Response):
        return resp.raw
    else:
        return resp


def _check_content_size_and_resolve_redirects(url: str, max_size: int = 10*1024*1024):
    try:
        with closing(request_with_retries('HEAD', url, allow_redirects=True)) as resp:
            resp.raise_for_status()
            content_length = int(resp.headers.get('content-length', 0))
            content_type = resp.headers.get('content-type', '').split(';')[0].strip()
            if content_length > max_size:
                raise MemoryError(f"File is too large (> {max_size} bytes)")
            if content_type != 'text/html':
                raise ValueError(f"File doesn't look like sane HTML (Content-Type: {content_type})")

            # Return the URL to the final destination in case we were redirected
            return resp.url

    except BaseException as e:
        raise e


def get_tar_file_manifest(
        tar_url: str,
        index_suffix='.manifest-md5',
        checksum_type='md5') -> List[Dict[str, str]]:
    """
    Given a URL to a tar archive or .tar.manifest-md5 file, fetch the corresponding
    .manifest-md5 and return a list of (checksum, filename) pairs.
    :param tar_url: The URL to the tar file or .tar.manifest-md5 (eg https://example.com/data.tar,
                    https://example.com/data.tar.gz or https://example.com/data.tar.manifest-md5)
    :type tar_url: str
    :param index_suffix: The suffix to add to the URL path to find the manifest
                         file.
    :type index_suffix: str
    :return: A list of tuples, (checksum, filename)
    :rtype: Tuple[List[str], List[str]]
    """
    def _discover_manifest_url(tar_url):
        murl = urlparse(tar_url)
        murl = murl._replace(path=f'{murl.path}.manifest-md5')
        murl = murl.geturl()
        return murl

    fn = Path(urlparse(tar_url).path).name
    if fn.endswith('.manifest-md5'):
        manifest_url = tar_url
    else:
        manifest_url = _discover_manifest_url(tar_url)

    try:
        # req = requests.get(manifest_url)
        # req.raise_for_status()
        # text = requests.get(manifest_url).text
        text = get_url_filelike(manifest_url).read().decode('utf-8')
    except BaseException as e:
        raise e

    file_index = []
    for line in text.splitlines():
        checksum, filename = line.split('  ', 1)
        file_index.append({'filepath': os.path.normpath(filename.strip()),
                           'checksum': f'{checksum_type}:{checksum.strip()}'})
    return file_index
