import random
import string
import uuid
import base64
from collections import OrderedDict
import json
from basehash import base62
import requests
import cgi
import os
from operator import itemgetter
from functools import cmp_to_key
from typing import Mapping, Sequence

from urllib.parse import urlparse

from django.urls import reverse
from django.utils.http import urlencode

from rest_framework.request import Request


def sh_bool(boolean):
    """
    Formats a boolean to be passed to a bash script environment (eg run_job.sh)
    :param boolean:
    :type boolean:
    :return: 'yes' or 'no'
    :rtype: str
    """
    if boolean:
        return 'yes'
    else:
        return 'no'


def url_safe_base64_uuid() -> str:
    padded_base64_uuid = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return padded_base64_uuid.decode('ascii').replace('=', '')


def url_safe_base62_uuid() -> str:
    return base62().encode(uuid.uuid4().int)


def generate_uuid() -> str:
    return url_safe_base62_uuid()


def generate_secret_key(length=255) -> str:
    return ''.join(
        [random.choice(string.ascii_letters + string.digits)
         for _ in range(length)]
    )


def b64uuid_to_uuid(b64uuid: str, regenerate_padding=True) -> uuid.UUID:
    if regenerate_padding:
        pad_chars = (24 - len(b64uuid)) * '='
        b64uuid += pad_chars
    as_str = str(b64uuid)
    as_bytes = base64.urlsafe_b64decode(as_str)
    return uuid.UUID(bytes=as_bytes)


def b62encode(text: str) -> str:
    return base62().encode(int.from_bytes(text.encode(), byteorder='big'))


def ordereddicts_to_dicts(d: OrderedDict) -> dict:
    """
    Turns nested OrderedDicts into plain dicts (eg, for the purpose of
    assertDictEqual dict comparison).
    """
    return json.loads(json.dumps(d))


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


def reverse_querystring(view, urlconf=None, args=None, kwargs=None,
                        current_app=None, query_kwargs=None):
    """
    Custom reverse to handle query strings.

    Usage:
        reverse('app.views.my_view', kwargs={'pk': 123}, query_kwargs={'search', 'Bob'})

    https://gist.github.com/benbacardi/227f924ec1d9bedd242b
    """
    base_url = reverse(view, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    if query_kwargs:
        return '{}?{}'.format(base_url, urlencode(query_kwargs))
    return base_url


def unique(l):
    return list(set(l))


def multikeysort(items: Sequence[Mapping], columns: Sequence[str], reverse=False) -> Sequence[Mapping]:
    """
    Takes a list of dictionaries and returns a list sorted by the value
    associated with keys specified in 'columns'.

    Alternative is to just use pydash.sort_by instead ...
    (https://pydash.readthedocs.io/en/latest/api.html#pydash.collections.sort_by)

    :param items:
    :type items:
    :param columns:
    :type columns:
    :param reverse:
    :type reverse:
    :return: A sorted list.
    :rtype: list of dicts
    """
    i = itemgetter
    comparers = [
        ((i(col[1:].strip()), -1) if col.startswith('-') else (i(col.strip()), 1))
        for col in columns
    ]

    def cmp(a, b):
        return (a > b) - (a < b)

    def comparer(left, right):
        comparer_iter = (
            cmp(fn(left), fn(right)) * mult
            for fn, mult in comparers
        )
        return next((result for result in comparer_iter if result), 0)

    return sorted(items, key=cmp_to_key(comparer), reverse=reverse)


def laxy_sftp_url(job, path: str = None) -> str:
    """
    Generate internal laxy+sftp:// URL strings based on a job and file path.

    :param job: A Job instance
    :type job: models.Job
    :param path: The path/filename
    :type path: str
    :return: The internal laxy+sftp:// URL
    :rtype: str
    """
    if job.compute_resource is None:
        raise ValueError("Job has no compute_resource defined. "
                         "Cannot generate laxy+sftp:// URL since it requires a compute_resource ID.")

    url = f'laxy+sftp://{job.compute_resource.id}/{job.id}'

    if path:
        url = f'{url}/{path}'

    return url


def get_content_type(request: Request) -> str:
    """
    Returns the simple Content-Type (MIME type/media type) for an HTTP Request
    object.

    :param request: The request.
    :type request: Request
    :return: The content type, eg text/html or application/json
    :rtype: str
    """
    return request.content_type.split(';')[0].strip()
