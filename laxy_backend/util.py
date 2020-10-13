from typing import Union, Tuple, Sequence
import traceback
import random
import string
import re
import shlex
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
import unicodedata
from text_unidecode import unidecode

from urllib.parse import urlparse, unquote
from cache_memoize import cache_memoize

import django
from django.urls import reverse
from django.utils.http import urlencode

from typing_extensions import Literal
from rest_framework.request import Request

from . import models
from pathlib import Path


def has_method(obj, method_name: str) -> bool:
    """
    Returns True if the provided object (`obj`) has the named method (`method_name`).
    """
    return callable(getattr(obj, method_name, None))


def sh_bool(boolean: bool) -> Literal["yes", "no"]:
    """
    Formats a boolean to be passed to a bash script environment (eg run_job.sh)

    :param boolean: A boolean flag (True or False)
    :type boolean: bool
    :return: 'yes' or 'no'
    :rtype: str
    """
    if boolean:
        return "yes"

    return "no"


def url_safe_base64_uuid() -> str:
    padded_base64_uuid = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return padded_base64_uuid.decode("ascii").replace("=", "")


def url_safe_base62_uuid() -> str:
    return base62().encode(uuid.uuid4().int)


def generate_uuid() -> str:
    return url_safe_base62_uuid()


def generate_secret_key(length=255) -> str:
    return "".join(
        [random.choice(string.ascii_letters + string.digits) for _ in range(length)]
    )


def b64uuid_to_uuid(b64uuid: str, regenerate_padding=True) -> uuid.UUID:
    if regenerate_padding:
        pad_chars = (24 - len(b64uuid)) * "="
        b64uuid += pad_chars
    as_str = str(b64uuid)
    as_bytes = base64.urlsafe_b64decode(as_str)
    return uuid.UUID(bytes=as_bytes)


def b62encode(text: str) -> str:
    return base62().encode(int.from_bytes(text.encode(), byteorder="big"))


def ordereddicts_to_dicts(d: OrderedDict) -> dict:
    """
    Turns nested OrderedDicts into plain dicts (eg, for the purpose of
    assertDictEqual dict comparison).
    """
    return json.loads(json.dumps(d))


@cache_memoize(timeout=3 * 60 * 60, cache_alias="memoize")
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
    :return: A tuple of (filename, size) (the download filename and size in bytes)
    :rtype: (str, int)
    """
    scheme = urlparse(url).scheme.lower()
    file_size = None
    filename = None
    if scheme in ["http", "https"]:
        try:
            head = requests.head(url, **kwargs)
            filename_header = cgi.parse_header(
                head.headers.get("Content-Disposition", "")
            )[-1]
            file_size = head.headers.get("Content-Length", None)
            if file_size is not None:
                file_size = int(file_size)
            if "filename" in filename_header:
                filename = filename_header.get("filename")
        except:
            pass

    if filename is None or (scheme == "file" or scheme == "ftp" or scheme == "sftp"):
        filename = os.path.basename(urlparse(url).path)

    # TODO: Should we disallow this, given that it actually reads the local filesystem and may be
    #  unsafe or an information leak if used with arbitrary user supplied URLs ?
    if scheme == "file":
        file_size = os.path.getsize(urlparse(url).path)

    if not filename:
        raise ValueError("Could not find a filename for: %s" % url)

    filename = filename.strip()

    if sanitize_name:
        filename = sanitize_filename(filename)

    return filename, file_size


def reverse_querystring(
    view, urlconf=None, args=None, kwargs=None, current_app=None, query_kwargs=None
):
    """
    Custom Django `reverse` to handle query strings. Turns a view function into a URL,
    with a properly encoded query string generated from the query_kwargs dict.

    Usage:
        reverse('app.views.my_view', kwargs={'pk': 123}, query_kwargs={'search', 'Bob'})

    https://gist.github.com/benbacardi/227f924ec1d9bedd242b
    """
    base_url = reverse(
        view, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app
    )
    if query_kwargs:
        return "{}?{}".format(base_url, urlencode(query_kwargs))
    return base_url


def unique(l):
    return list(set(l))


def multikeysort(
    items: Sequence[Mapping], columns: Sequence[str], reverse=False
) -> Sequence[Mapping]:
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
        ((i(col[1:].strip()), -1) if col.startswith("-") else (i(col.strip()), 1))
        for col in columns
    ]

    def cmp(a, b):
        return (a > b) - (a < b)

    def comparer(left, right):
        comparer_iter = (cmp(fn(left), fn(right)) * mult for fn, mult in comparers)
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
        raise ValueError(
            "Job has no compute_resource defined. "
            "Cannot generate laxy+sftp:// URL since it requires a compute_resource ID."
        )

    url = f"laxy+sftp://{job.compute_resource.id}/{job.id}"

    if path:
        url = f"{url}/{path}"

    return url


def is_valid_laxy_sftp_url(url):
    try:
        scheme = urlparse(url).scheme.lower()
        if scheme != "laxy+sftp":
            return False
        compute_resource_id = urlparse(url).netloc
        if compute_resource_id:
            compute = models.ComputeResource.objects.get(id=compute_resource_id)
            if not compute:
                return False
        if urlparse(url).path == "":
            return False
    except:
        return False

    return True


def split_laxy_sftp_url(
    location, to_objects=False
) -> Union[Tuple[str], Tuple[django.db.models.Model]]:
    valid_scheme = "laxy+sftp"
    location = str(location)

    url = urlparse(location)
    scheme = url.scheme
    if scheme != valid_scheme:
        raise ValueError(
            f"{location} is not a valid {valid_scheme}:// URL. Wrong scheme."
        )
    if "." in url.netloc:
        raise ValueError(
            f"{location} is not a valid {valid_scheme}:// URL. "
            "Invalid ComputeResource ID format."
        )
    # use netloc not hostname, since hostname forces lowercase
    compute = url.netloc
    _, job, path_file = url.path.split("/", 2)
    path = Path(path_file).parent
    filename = Path(path_file).name

    if "." in compute:
        raise ValueError(
            f"{location} is not a valid {valid_scheme}:// URL. "
            "Invalid ComputeResource ID format."
        )

    if "." in job:
        raise ValueError(
            f"{location} is not a valid {valid_scheme}:// URL. "
            "Invalid Job ID format."
        )

    if to_objects:
        try:
            compute = models.ComputeResource.objects.get(id=compute)
        except models.ComputeResource.DoesNotExist as e:
            raise models.ComputeResource.DoesNotExist(
                f"ComputeResource {compute} does not exist. (file.location={location})"
            )
        try:
            job = models.Job.objects.get(id=job)
        except models.Job.DoesNotExist as e:
            raise models.Job.DoesNotExist(
                f"Job {job} does not exist. (file.location={location})"
            )

    return compute, job, path, filename


def get_content_type(request: Request) -> str:
    """
    Returns the simple Content-Type (MIME type/media type) for an HTTP Request
    object.

    :param request: The request.
    :type request: Request
    :return: The content type, eg text/html or application/json
    :rtype: str
    """
    return request.content_type.split(";")[0].strip()


def get_traceback_message(ex: BaseException) -> Union[str]:
    message = ""
    if hasattr(ex, "message") and ex.message:
        message = ex.message
    else:
        message = str(ex)

    if hasattr(ex, "__traceback__"):
        tb = ex.__traceback__
        message = "%s - Traceback: %s" % (
            message,
            "".join(traceback.format_list(traceback.extract_tb(tb))),
        )

    return message


def sanitize_filename(
    filename: str,
    valid_filename_chars: str = None,
    replace: dict = None,
    max_length: int = 255,
    unicode_to_ascii=False,
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
        replace = {" ": "_"}

    if unquote_urlencoding:
        filename = unquote(filename)

    if unicode_to_ascii:
        filename = unidecode(filename)

    # replace spaces or other characters in the replacement dict
    for old, new in replace.items():
        filename = filename.replace(old, new)

    # keep only valid ascii chars
    cleaned_filename = (
        unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode()
    )

    # keep only valid chars
    cleaned_filename = "".join(c for c in cleaned_filename if c in valid_filename_chars)

    return cleaned_filename[:max_length]


def truncate_fastq_to_pair_suffix(fn: str) -> str:
    """
    Turn a XXXBLAFOO_R1.fastq.gz filename into XXXBLAFOO_R1.
    """
    extensions = [
        r"_001\.fastq\.gz$",  # Default Illumina
        r"\.fastq\.gz$",  # ENA/SRA
        r"\.fasta\.gz$",  # occasionally we get FASTA format reads
        r"\.fq\.gz$",  # BGI does this, it seems
        r"\.fastq$",  # Occasionally we need to take uncompressed fastqs
        r"\.fasta$",  # why not
    ]

    # Try removing all of these extensions
    for ext in extensions:
        fn = re.sub(ext, "", fn, 1)

    return fn


def simplify_fastq_name(filename: str) -> str:
    """
    Given a FASTQ filename XXXBLAFOO_R1.fastq.gz, return something like
    the 'sample name' XXXBLAFOO. Should work with typical naming used by 
    Illumina instrument and SRA/ENA FASTQ files.
    """
    fn = truncate_fastq_to_pair_suffix(filename)
    # eg remove suffix _L002_R1 or L003_2 or _2, or just _R2
    fn = re.sub(r"_(R)?[1-2]$|_L[0-9][0-9][0-9]_(R)?[1-2]$", "", fn, 1)
    return fn


def longest_common_prefix(string_list: Sequence[Sequence]):
    return os.path.commonprefix(string_list)


def generate_cluster_stack_name(job):
    """
    Given a job, generate a name for an associated compute cluster resource.

    Since this becomes an AWS (or OpenStack?) Stack name via CloudFormation
    it can only contain alphanumeric characters (upper and lower) and hyphens
    and cannot be longer than 128 characters.

    :param job: A Job instance (with ComputeResource assigned)
    :type job: Job
    :return: A cluster ID to use as the stack name.
    :rtype: str
    """
    return 'cluster-%s----%s' % (job.compute_resource.id, job.id)