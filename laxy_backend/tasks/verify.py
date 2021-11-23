from typing import Sequence, Union, Iterable
from contextlib import closing
from collections import namedtuple
from datetime import datetime
from urllib.parse import urlparse
from io import BytesIO, StringIO, BufferedRandom, BufferedReader

import hashlib
import xxhash

from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (
    Ignore,
    InvalidTaskError,
    TimeLimitExceeded,
    SoftTimeLimitExceeded,
)

from ..models import (
    Job,
    File,
    FileLocation,
    EventLog,
    get_compute_resource_for_location,
    get_storage_class_for_location,
    ComputeResource,
    get_primary_compute_location_for_files,
    job_path_on_compute,
)

from ..util import get_traceback_message

logger = get_task_logger(__name__)

VerificationMode = namedtuple(
    "VerificationMode",
    ["NONE", "SIZE", "CHECKSUM", "CHECKSUM_ELSE_SIZE", "CHECKSUM_IF_SET",],
    # TODO: Once we are using Python 3.7+ we can set defaults here, add (),
    #       change this to VerifMode and avoid defining VerifMode seperately below
    # defaults=["checksum", "checksum_else_size", "checksum_if_set", "size",],
)  # ()

VerifMode = VerificationMode(
    NONE="none",
    SIZE="size",
    CHECKSUM="checksum",
    CHECKSUM_ELSE_SIZE="checksum_else_size",
    CHECKSUM_IF_SET="checksum_if_set",
)


def get_checksum_and_size(filelike, hash_type="md5", blocksize=8192):
    hashers = {"md5": hashlib.md5, "sha512": hashlib.sha512, "xx64": xxhash.xxh64}

    hasher = hashers.get(hash_type, None)
    if hasher is None:
        raise ValueError(f"Unsupported hash_type: {hash_type}")
    else:
        hasher = hasher()

    # Make the chunk_size an integral of the preferred block_size for the hash algorithm
    chunk_size = max(blocksize // hasher.block_size, 1) * hasher.block_size

    # with BufferedReader(filelike, buffer_size=chunk_size * 128) as fh:
    with filelike as fh:
        byte_count = 0
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            hasher.update(chunk)
            byte_count += len(chunk)

    checksum = hasher.hexdigest()
    return f"{hash_type}:{checksum}", byte_count


def _validate_verification_prereqs(
    file: File, location: Union[str, FileLocation, None] = None
) -> bool:
    if location is None:
        location = file.location

    if isinstance(location, FileLocation):
        location = str(location)
    # We allow verification at location URLs that might not exist as FileLocations in the database
    # yet, since we want to be able to validate a copy before we make it a concrete replica.
    # elif not file.locations.filter(url=location).exists():
    #     # logger.error(f"File {file.id} does not have location: {location}")
    #     raise ValueError(f"File {file.id} does not have location: {location}")

    if urlparse(location).scheme != "laxy+sftp":
        # Only verifying 'laxy+sftp' URLs at this stage.
        raise NotImplementedError(
            "Verification only implemented for 'laxy+sftp://' URLs"
        )

    return file, location


def verify_checksum(
    file: File, location: Union[str, FileLocation, None] = None,
) -> bool:
    """
    Verifies a file stored at a particular FileLocation by comparing the checksum of the
    remote data to the File.checksum value. Usually results in a full read of the file content
    (unless the storage backend has a method to query the checksum required, as with some
     Object Storage services).

    :param file: The File model object.
    :type file: laxy_backend.models.File
    :param location: The file location to verify, as a string or FileLocation object
    :type location:  Union[str, laxy_backend.models.FileLocation, None]
    :return: True if checksum of remote file matches the recorded checksum
    :rtype: bool
    """
    if not file.checksum:
        return None

    file, location = _validate_verification_prereqs(file, location)

    verified = False
    filelike = file._file(location)
    with closing(file._file(location)) as filelike:
        checksum_at_location, size = get_checksum_and_size(filelike)
    verified = checksum_at_location == file.checksum

    return verified


def verify_size(file: File, location: Union[str, FileLocation, None] = None,) -> bool:
    """
    Verifies that the reported size of a file stored at a particular FileLocation 
    matches the recorded `File.size` in the database.

    :param file: The File model object.
    :type file: laxy_backend.models.File
    :param location: The file location to verify, as a string or FileLocation object
    :type location:  Union[str, laxy_backend.models.FileLocation, None]
    :return: True if checksum of remote file matches the recorded checksum
    :rtype: bool
    """

    file, location = _validate_verification_prereqs(file, location)
    recorded_size = file.metadata.get("size", None)

    verified = False
    with closing(file._file(location)) as filelike:
        if hasattr(filelike, "size") and recorded_size is not None:
            verified = int(filelike.size) == int(file.metadata["size"])

    return verified


def verify(
    file: File,
    location: Union[str, FileLocation, None] = None,
    verify_on=VerifMode.CHECKSUM,
) -> bool:
    """
    Verifies a file stored at a particular FileLocation. By default compares the checksum of the
    remote data to the File.checksum value (verify_on=VerifMode.CHECKSUM), but can also verify
    based only on the reported file size (verify_on=VerifMode.SIZE), or use size as a fallback when
    File.checksum is not set (VeriftMode.CHECKSUM_ELSE_SIZE).

    Optionally can set the file size metadata if verification is successful and the
    size hasn't been recorded.

    :param file: The File model object.
    :type file: laxy_backend.models.File
    :param location: The file location to verify, as a string or FileLocation object
    :type location:  Union[str, laxy_backend.models.FileLocation, None]
    :param verify_on: Mode of verification - 'checksum' to strictly verify on checksum, 
                      'checksum_if_set' to verify on checksum if the checksum is set, otherwise 
                      fallback to file size. 'size' to verify based only on file size.
    :return: True if checksum of remote file matches the recorded checksum
    :rtype: bool
    """
    verified = False

    if verify_on == VerifMode.NONE:
        return True

    elif verify_on == VerifMode.SIZE:
        verified = verify_size(file, location)

    elif verify_on == VerifMode.CHECKSUM:
        verified = verify_checksum(file, location)

    elif verify_on == VerifMode.CHECKSUM_ELSE_SIZE:
        if file.checksum:
            verified = verify_checksum(file, location)
        else:
            verified = verify_size(file, location)

    elif verify_on == VerifMode.CHECKSUM_IF_SET:
        if file.checksum:
            verified = verify_checksum(file, location)
        else:
            verified = True

    return verified


@shared_task(
    name="verify_task",
    queue="low-priority",
    bind=True,
    track_started=True,
    retry_backoff=True,
    default_retry_delay=10 * 60,
    max_retries=3,
)
def verify_task(self, task_data=None, **kwargs):
    if task_data is None:
        raise InvalidTaskError("task_data is None")

    try:
        filelocation_id = task_data.get("filelocation_id", None)
        file_id = task_data.get("file_id", None)
        location = task_data.get("location", None)
        verify_on = task_data.get("verify_on", VerifMode.CHECKSUM_ELSE_SIZE)

        if filelocation_id and location:
            raise ValueError(
                "Please provide only filelocation_id or location, not both."
            )

        if filelocation_id:
            location = FileLocation.objects.get(id=filelocation_id)

        file = File.objects.get(id=file_id)
        started_at = timezone.now()
        verified = verify(file, location, verify_on=verify_on)
        finished_at = timezone.now()
        walltime = (finished_at - started_at).total_seconds()
        url = location
        url = str(location)

        task_data["result"] = {
            "verified": verified,
            "operation": "verify",
            "location": url,
            "started_time": started_at.isoformat(),
            "finished_time": finished_at.isoformat(),
            "walltime_seconds": walltime,
        }
        if file.size is not None:
            kbps = (file.size / 1000) / walltime
            task_data["result"]["rate_kbps"] = kbps

        task_succeeded = True
    except (ValueError, NotImplementedError,) as ex:
        task_succeeded = False
        message = get_traceback_message(ex)

    except BaseException as e:
        task_succeeded = False
        message = get_traceback_message(e)
        raise self.retry(exc=ex)

    if not task_succeeded:
        self.update_state(state=states.FAILURE, meta=message)
        raise Exception(message)
        # raise Ignore()

    return task_data
