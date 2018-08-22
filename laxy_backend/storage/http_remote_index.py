import logging
from typing import List, Tuple, Pattern, Union, Dict
from collections import defaultdict
from urllib.parse import urljoin, urlparse
import re
import os
import requests
from requests import HTTPError, Response
from bs4 import BeautifulSoup
import magic  # python-magic

from laxy_backend.tasks.download import request_with_retries

logger = logging.getLogger(__name__)


def is_archive_link(url: str, content_head: bytes = None) -> bool:
    """
    Attempts to determine if a given URL is a TAR file based on file extensions
    or the first 512 bytes of content.

    :param url: The URL of interest
    :type url: str
    :param content_head: Optional head content (not HTTP HEAD, actual body content)
    :type content_head: bytes
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

    if content_head is None:
        resp = get_url_streaming(url)
        resp.raise_for_status()
        content_head = resp.raw.read(512)
        return _smells_like_tar(content_head)

    return False


def get_url_streaming(url, headers=None, auth=None):
    headers = headers or {}
    response = request_with_retries(
        'GET', url,
        stream=True,
        headers=headers,
        auth=auth)
    response.raw.decode_content = True
    return response


def grab_links_from_page(url: str,
                         regex: Union[str, Pattern] = '^https?://|^ftp://',
                         ignore: str = '\/\?C=.;O=.') -> Tuple[List[str], List[str]]:
    """
    Parses a remote HTTP(s) index page containing links, returns
    a list of the links, filtered by provided `regex`. Works best
    with simple HTML pages of links, like the default Apache directory
    listing page.

    :param url: The index page URL.
    :type url: str
    :param regex: A regular expression (as compiled regex or string) that links
                  must match.
    :type regex: str | Pattern
    :param ignore: Ignore URLs matching this regex pattern
                   (compiled regex or string)
    :type ignore: str | Pattern
    :return: The filtered list of links (URLs) on the page, as a tuple. First
             element is the list (presumed) to be links to downloadable files,
             the second is a list of (presumed) 'directories' that are likely
             to lead to additional index pages.
    :rtype: Tuple[List[str], List[str]]
    """

    if isinstance(regex, str):
        regex = re.compile(regex)
    if isinstance(ignore, str):
        ignore = re.compile(ignore)

    try:
        resp = requests.get(url)
        resp.raise_for_status()
        text = resp.text

    except BaseException as e:
        raise e

    soup = BeautifulSoup(text, 'html.parser')

    file_urls = []
    dir_urls = []
    for a in soup.find_all('a'):
        href = a.get('href')
        u = str(href)
        if href is not None and "://" not in href:
            # convert to full URL, not just path
            u = urljoin(url, href)
        if regex.search(u) and not ignore.search(u):
            if urlparse(u).path.endswith('/'):
                dir_urls.append(u)
            else:
                file_urls.append(u)

    return file_urls, dir_urls


def get_tar_file_manifest(
        tar_url: str,
        index_suffix='.manifest-md5',
        checksum_type='md5') -> List[Dict[str, str]]:
    """
    Given a URL to a tar archive , fetch the corresponding .manifest-md5
    and return a list of checksum, filename pairs.
    :param tar_url: The URL to the tar file (eg https://example.com/data.tar or
                    https://example.com/data.tar.gz)
    :type tar_url: str
    :param index_suffix: The suffix to add to the URL path to find the manifest
                         file.
    :type index_suffix: str
    :return: A list of tuples, (checksum, filename)
    :rtype: Tuple[List[str], List[str]]
    """
    def _discover_manifest_url(tar_url):
        murl = urlparse(tar_url)
        murl = murl._replace(path='%s.manifest-md5' % murl.path)
        murl = murl.geturl()
        return murl

    manifest_url = _discover_manifest_url(tar_url)

    try:
        req = requests.get(manifest_url)
        req.raise_for_status()
        text = requests.get(manifest_url).text
    except BaseException as e:
        raise e

    file_index = []
    for line in text.splitlines():
        checksum, filename = line.split('  ', 1)
        file_index.append({'filepath': os.path.normpath(filename.strip()),
                           'checksum': f'{checksum_type}:{checksum.strip()}'})
    return file_index
