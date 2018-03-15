# from __future__ import absolute_import, print_function
import logging
from typing import Union
import os
import random
import time
from copy import copy
from pathlib import Path
import shutil
import tempfile
from contextlib import closing
import yaml
from basehash import base62
import xxhash
import cgi
import backoff
from toolz.dicttoolz import merge as merge_dicts
from http.client import responses as response_codes
import requests
from requests.auth import HTTPBasicAuth
import urllib.request
from urllib.parse import urlparse
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (Ignore,
                               InvalidTaskError,
                               TimeLimitExceeded,
                               SoftTimeLimitExceeded)

from ..models import Job, ComputeResource, File

from celery.utils.log import get_task_logger
from ..util import b62encode, find_filename_and_size_from_url

logger = get_task_logger(__name__)


def _raise_request_exception(response):
    e = requests.exceptions.RequestException(response=response)
    e.message = "Request failed (%s) %s : %s" % (response.status_code,
                                                 response.reason,
                                                 response.url)
    raise e


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
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
                                         prefix=filename,
                                         delete=False) as tmpfile:
            tmpfilepath = str(Path(directory, tmpfile.name))
            urllib.request.urlretrieve(url, filename=tmpfilepath)
            shutil.move(tmpfilepath, filepath)
            return filepath

    # We download to a temporary file then move it once
    # the download is complete
    tmpfilepath = None
    status_code = None
    try:
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
                                             prefix=filename,
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


# TODO: Look at using an existing caching backend:
#       eg https://github.com/miku/python-cachedurl
#       or http://cachecontrol.readthedocs.io/en/latest/storage.html#filecache
#       or https://docs.djangoproject.com/en/2.0/topics/cache/#the-low-level-cache-api
#       or Squid as a proxy for caching, properly configure for large files
#       - disadvantages of most of these is that we actually want to use
#         the cached files on disk with meaningful names and structure directly
#         and these generally won't let use control the structure of the disk
#         cache
@shared_task(bind=True, track_started=True)
def download_file(self, file_id: Union[str, File]):
    if isinstance(file_id, str):
        file = File.objects.get(id=file_id)
    elif isinstance(file_id, File):
        file = file_id
    cache_path = getattr(settings, 'FILE_CACHE_PATH')
    # filename = '%s.%s' % (file.name, file.id)
    filename = b62encode(file.location)
    cached_file = str(Path(cache_path, filename))
    download_url(file.location, cached_file)

    return cached_file
