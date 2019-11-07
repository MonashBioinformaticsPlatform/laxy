import fnmatch
import traceback
from django.db import transaction
from typing import Sequence, Union
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import xxhash
import logging
import os
from os.path import join, expanduser
import random
import time
import json
import base64
from io import (BytesIO, StringIO,
                BufferedRandom, BufferedReader)
from copy import copy
from contextlib import closing

from django.conf import settings

from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (Ignore,
                               InvalidTaskError,
                               TimeLimitExceeded,
                               SoftTimeLimitExceeded)

from ..models import (Job,
                      File,
                      FileLocation,
                      EventLog,
                      get_compute_resource_for_location,
                      get_storage_class_for_location)
from ..util import get_traceback_message

logger = get_task_logger(__name__)


@shared_task(bind=True, track_started=True)
def bulk_copy_job_task(self, task_data=None, **kwargs):
    from ..models import File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get('job_id')
    to_location = task_data.get('new_location')

    # TODO: Complete this task - probably should use rsync, verify transfer worked (eg, rsync twice with checksums and
    # non-zero error code), then update all input_files and output_files default FileLocations in a transaction.
    # See: scripts/ad-hoc-migrations/update-job-location.py for job location update code
    raise NotImplementedError()


def location_path_on_compute(location, compute):
    url = urlparse(location)
    if compute is None:
        raise Exception(f"Cannot extract ComputeResource ID from: {location}")
    base_dir = compute.extra.get('base_dir', getattr(settings, 'DEFAULT_JOB_BASE_PATH'))
    # TODO: Path(url.path).relative_to('/') isn't always correct, eg for something at an https:// URL
    #       without the job_id in the path, we need to include the job_id in the path when copying to
    #       a laxy+sftp:// url.
    file_path = str(Path(base_dir) / Path(url.path).relative_to('/'))
    return file_path


def get_checksum_and_size(filelike, hash_type='md5', blocksize=8192):
    hashers = {'md5': hashlib.md5,
               'sha512': hashlib.sha512,
               'xx64': xxhash.xxh64}

    hasher = hashers.get(hash_type, None)
    if hasher is None:
        raise ValueError(f"Unsupported hash_type: {hash_type}")
    else:
        hasher = hasher()

    # Make the chunk_size an integral of the preferred block_size for the hash algorithm
    chunk_size = max(blocksize // hasher.block_size, 1) * hasher.block_size

    # We read buffer ahead - this seems to be more reliable for files over the network
    with BufferedReader(filelike, buffer_size=chunk_size*128).raw as fh:
        byte_count = 0
        for chunk in iter(lambda: fh.read(chunk_size), b''):
            hasher.update(chunk)
            byte_count += len(chunk)

    checksum = hasher.hexdigest()
    return f'{hash_type}:{checksum}', byte_count


def verify(file: File, location: Union[str, FileLocation, None] = None, set_size: bool = True) -> bool:
    """
    Verifies the data at a particular FileLocation but comparing the checksum of the
    remote data to the File.checksum value.

    Optionally can set the file size metadata if verification is successful and the
    size hasn't been recorded.

    :param file: The File model object.
    :type file: laxy_backend.models.File
    :param location: The file location to verify, as a string or FileLocation object
    :type location:  Union[str, laxy_backend.models.FileLocation, None]
    :param set_size: Add the size metadata if verification is successful and size metadata is absent.
    :type set_size: bool
    :return: True if checksum of remote file matches the recorded checksum
    :rtype: bool
    """
    if not file.checksum:
        return None

    if location is None:
        location = file.location

    if isinstance(location, FileLocation):
        location = location.url
    elif not file.locations.filter(url=location).exists():
        # logger.error(f"File {file.id} does not have location: {location}")
        raise ValueError(f"File {file.id} does not have location: {location}")

    if urlparse(location).scheme != 'laxy+sftp':
        # Only verifying 'laxy+sftp' URLs at this stage.
        return True

    storage = get_storage_class_for_location(location)
    compute_for_loc = get_compute_resource_for_location(location)
    path_on_storage = location_path_on_compute(location, compute_for_loc)
    with storage.open(path_on_storage) as filelike:
        checksum_at_location, size = get_checksum_and_size(filelike)

    checksum_matches = checksum_at_location == file.checksum

    if set_size and checksum_matches and file.size is None:
        file.metadata['size'] = size
        file.save()

    return checksum_matches


@shared_task(bind=True, track_started=True)
def verify_task(self, task_data=None, **kwargs):

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    try:
        filelocation_id = task_data.get('filelocation_id', None)
        file_id = task_data.get('file_id', None)
        location = task_data.get('location', None)

        if filelocation_id and location:
            raise ValueError("Please provide only filelocation_id or location, not both.")

        if filelocation_id:
            location = FileLocation.objects.get(id=filelocation_id)

        file = File.objects.get(id=file_id)
        started_at = datetime.now()
        verified = verify(file, location)
        finished_at = datetime.now()
        walltime = (finished_at - started_at).total_seconds()
        url = location
        if isinstance(location, FileLocation):
            url = location.url

        task_data['result'] = {'verified': verified,
                               'operation': 'verify',
                               'location': url,
                               'started_time': started_at.isoformat(),
                               'finished_time': finished_at.isoformat(),
                               'walltime_seconds': walltime}
        if file.size is not None:
            kbps = (file.size / 1000) / walltime
            task_data['result']['rate_kbps'] = kbps

        task_succeeded = True

    except BaseException as e:
        task_succeeded = False
        message = get_traceback_message(e)

    if not task_succeeded:
        self.update_state(state=states.FAILURE, meta=message)
        raise Exception(message)
        # raise Ignore()

    return task_data


def copy_file_to(file: File,
                 to_location: str,
                 make_default=False,
                 verification_type='immediate',
                 deleted_failed_destination_copy=True) -> File:

    _verification_types = ['immediate', 'async', 'none']
    if verification_type not in _verification_types:
        raise ValueError(f'verification_type must be one of: {", ".join(_verification_types)}')

    if file.deleted:
        logger.warning(f"{file.id} is marked as deleted. Not attempting copy operation.")
        return file

    with transaction.atomic():
        from_location = file.location

        # TODO: Most of the code here assumes the laxy+sftp:// scheme
        #       Refactor parts onto the File or ComputeResource models and
        #       deal with other supported schemes.

        # TODO: If scheme is laxy+sftp and netloc is the same between from_location and to_location,
        #       skip using storage.save and use fabric to do a 'local' copy on the ComputeResource
        #       (probably via rsync). Think about how to detect if we should do a node-local copy
        #       even if the ComputeResource IDs in the locations don't match (maybe same IP/hostname and
        #       same metadata.username, but different metadata.base_dir ?).
        #
        #       We could also do node-local moves, but only via `mv` if the operation is atomic
        #       [eg on the same filesystem] - otherwise we should do a copy-delete. Check same
        #       filesystem:
        #       https://unix.stackexchange.com/questions/44249/how-to-check-if-two-directories-or-files-belong-to-same-filesystem

        storage = get_storage_class_for_location(to_location)
        new_compute = get_compute_resource_for_location(to_location)

        try:
            new_path = location_path_on_compute(file.location, new_compute)
            # full_path = file.full_path
            # We need to check file existence, otherwise Django storages creates a new name rather than clobbering the
            # existing file !
            if not storage.exists(new_path):
                logger.info(f'Copying file to: {new_compute}:{new_path}')
                storage.save(new_path, file.file)

                if verification_type == 'immediate':
                    if not verify(file, to_location):
                        message = (f"File verification failed after copy ({file.id}: "
                                   f"{from_location} -> {to_location}). "
                                   f"Checksum for {to_location} doesn't match expected checksum: {file.checksum}")
                        if deleted_failed_destination_copy:
                            storage.delete(new_path)
                            logger.info(f"Deleted corrupted copy of {file.id} at {to_location}, "
                                        f"copy failed verification.")

                        logger.error(message)
                        raise Exception(message)
                elif verification_type == 'async':
                    # TODO: Trigger an async verification task.
                    #       What do we do if the location doesn't verify ?
                    #       Extra 'verified' flag or DateTime on FileLocation ?
                    #       Delete the new copy that failed verification, as long as original exists ?
                    #       Attempt copy again ?

                    # _task_data = dict(file_id=file.id, location=to_location)
                    # result = verify_task.apply_async(args=(_task_data,))

                    raise NotImplementedError()
                elif verification_type == 'none':
                    pass

            else:
                print(f'A file already exists at, skipping copy: {new_path}')

        except BaseException as e:
            logger.error(f'Failed to copy {file.id} from {from_location} to {to_location}')
            raise e

        file.location = to_location
        if not make_default:
            file.location = from_location

        file.save()

    return file


@shared_task(bind=True, track_started=True)
def copy_file_task(self, task_data=None, **kwargs):
    from ..models import File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    file_id = task_data.get('file_id')
    to_location = task_data.get('to_location')
    # verification_type = task_data.get('verification_type', 'immediate')
    make_default = False
    verification_type = 'none'
    deleted_failed = False

    start_time = None
    end_time = None
    try:
        file = File.objects.get(id=file_id)
        from_location = file.location
        try:
            start_time = datetime.utcnow()
            file = copy_file_to(file, to_location,
                                verification_type=verification_type,
                                deleted_failed_destination_copy=deleted_failed)
            end_time = datetime.utcnow()
            wall_time = (end_time - start_time).total_seconds()
        except BaseException as e:
            logger.error(f'Failed to copy {file_id} from {from_location} to {to_location}')
            raise e

        task_data.update(result={'file_id': file.id,
                                 'operation': 'copy',
                                 'to': to_location,
                                 'from': from_location,
                                 'start_time': start_time.isoformat(),
                                 'end_time': end_time.isoformat(),
                                 'walltime_seconds': wall_time})
    except BaseException as e:
        message = get_traceback_message(e)
        self.update_state(state=states.FAILURE, meta=message)
        raise Exception(message)

    return task_data
