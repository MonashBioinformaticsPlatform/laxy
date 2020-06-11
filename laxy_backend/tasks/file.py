import fnmatch
import traceback
import shlex
from typing import Sequence, Union, Iterable
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
from io import BytesIO, StringIO, BufferedRandom, BufferedReader
from copy import copy
from contextlib import closing
from collections import namedtuple

import numpy as np

from django.db import transaction
from django.conf import settings
from django.db.models import QuerySet

from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (
    Ignore,
    InvalidTaskError,
    TimeLimitExceeded,
    SoftTimeLimitExceeded,
)

# from .job import add_file_replica_records, remove_file_replica_records
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

from .verify import verify, verify_task, VerifMode
from ..util import get_traceback_message

logger = get_task_logger(__name__)


def _conservative_exp_backoff(n_retries, a=6, b=6.1, max_time=5 * 24 * 60 * 60):
    # From ~3 min (retry 1) to 3 days (retry 5) for a=6, b=6.1
    # max_time ensures we never exceed 5 days by default
    jittered_max = max_time + random.uniform(0, 60)
    jittered_delay = random.uniform(a, b) ** (n_retries + 2)
    # clamp between 1 and jittered_max
    return round(np.clip(jittered_delay, 1, jittered_max))


@shared_task(
    name="move_file_task",
    queue="low-priority",
    bind=True,
    track_started=True,
    default_retry_delay=60 * 60,
    max_retries=5,
    # autoretry_for=(IOError, OSError,),
    # We are using a custom exponential backoff instead of these
    # retry_backoff=600,  # 10 min, doubling each retry
    # retry_backoff_max=60*60*48,  # 48 hours
)
def move_file_task(self, task_data=None, **kwargs):
    """
    Moves a file from one location to another.

    Should run on a different celery queue to the default used for starting jobs.

    Steps:

      - Copy file from from_location to to_location
      - Verify transfer
      - Set file at to_location as the default
      - Delete file at from_location and remove from_location FileLocation record

    """
    from ..models import File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    file_id = task_data.get("file_id")
    from_location = task_data.get("from_location")
    to_location = task_data.get("to_location")
    make_default = True
    clobber = task_data.get("clobber", False)
    verify_on = task_data.get("verify_on", VerifMode.CHECKSUM_ELSE_SIZE)
    deleted_failed = True

    start_time = None
    end_time = None
    message = None
    result = {}
    task_succeeded = False
    retry = True  # this is set to False when the failure is considered permanent
    try:
        file = File.objects.get(id=file_id)

        if not file.locations.filter(url=from_location).exists():
            # TODO:
            # if verify(to_location, verify_on=verify_on):
            #     task_data["result"] = {"no_move_required": True,
            #                             "message": f"Skipping move of {file.id} - does not have requested source location {from_location} and already exists (verified) at destination {to_location}"}
            #     return task_data

            message = f"File {file.id} does not have location: {from_location} (task_id: {self.request.id})"
            raise ValueError(
                f"File {file.id} does not have location: {from_location} (task_id: {self.request.id})"
            )

        try:
            # self.update_state(state="PROGRESS", meta={"running": "copy_and_verify"})
            self.send_event("progress", step="copy_and_verify")
            if from_location != to_location:
                start_time = datetime.utcnow()
                # TODO: Upon task retries, this will clobber and retransfer even if the copy on
                #       earlier tries was successful (but a later step failed).
                #       Add a clobber='always' and clobber='size' option, that will do a file size
                #       check and only clobber if the sizes don't match.
                file = copy_file_to(
                    file,
                    from_location,
                    to_location,
                    make_default=make_default,
                    clobber=clobber,
                    verify_on=verify_on,
                    delete_failed_destination_copy=deleted_failed,
                )
                end_time = datetime.utcnow()
                wall_time = (end_time - start_time).total_seconds()

                result["copy"] = {
                    "file_id": file.id,
                    "operation": "copy",
                    "to": to_location,
                    "from": from_location,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "walltime_seconds": wall_time,
                }
            else:
                result["copy"] = {
                    "file_id": file.id,
                    "operation": "copy",
                    "to": to_location,
                    "from": from_location,
                    "skipped": True,
                }
        except BaseException as ex:
            logger.error(
                f"Failed to copy {file_id} from {from_location} to {to_location} (move_file:copy_and_verify)"
            )
            message = get_traceback_message(ex)
            raise ex

        try:
            # self.update_state(state="PROGRESS", meta={"running": "delete_old_copy"})
            self.send_event("progress", step="delete_old_copy")
            # TODO: Empty directories don't get removed when the last file is gone (do we care ?)
            file.delete_at_location(from_location, allow_delete_default=make_default)
            result["deleted_old_copy"] = True

        except BaseException as ex:
            logger.error(
                f"Failed delete remote file ({file.id}) at location {from_location} "
                f"(move_file:delete_old_copy)"
            )
            message = get_traceback_message(ex)
            raise ex

        task_succeeded = True
        result["success"] = True
        task_data["result"] = result

    except BaseException as ex:
        task_succeeded = False
        exc_type = type(ex).__name__
        if message is None:
            message = get_traceback_message(ex)
        print(message)
        if retry:
            raise self.retry(
                exc=ex, countdown=_conservative_exp_backoff(self.request.retries)
            )

    if not task_succeeded:
        raise Exception("\n".join([message, str(result)]))

    return task_data


def location_path_on_compute(
    location: str, compute: Union[None, ComputeResource] = None
) -> str:
    """
    Return the filesystem absolute path to a file on a (laxy+sftp://) ComputeResource.
    If compute is omitted, the ComputeResource is taken from the location url.
    If compute is provided, the path to the file as it would exist on that ComputeResource is returned.
    """

    url = urlparse(location)

    if compute is None and url.scheme == "laxy+sftp":
        compute_id = url.netloc
        compute = ComputeResource.objects.get(id=compute_id)

    if compute is None:
        raise Exception(f"Cannot extract ComputeResource ID from: {location}")

    base_dir = compute.extra.get("base_dir", getattr(settings, "DEFAULT_JOB_BASE_PATH"))
    # TODO: Path(url.path).relative_to('/') isn't always correct, eg for something at an https:// URL
    #       without the job_id in the path, we need to include the job_id in the path when copying to
    #       a laxy+sftp:// url.
    file_path = str(Path(base_dir) / Path(url.path).relative_to("/"))
    return file_path


def copy_file_to(
    file: File,
    from_location: Union[None, str, FileLocation],
    to_location: Union[str, FileLocation],
    make_default=False,
    clobber=False,
    verify_on=VerifMode.CHECKSUM,
    delete_failed_destination_copy=True,
) -> File:

    if verify_on not in list(VerifMode):
        raise ValueError(f'verify_on must be one of: {", ".join(list(VerifMode))}')

    if file.deleted:
        logger.warning(
            f"{file.id} is marked as deleted. Not attempting copy operation."
        )
        return file

    from_location = str(from_location)
    to_location = str(to_location)

    with transaction.atomic():
        if from_location is None:
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

        src_storage: SFTPStorage = get_storage_class_for_location(from_location)
        dst_storage: SFTPStorage = get_storage_class_for_location(to_location)
        dst_compute: ComputeResource = get_compute_resource_for_location(to_location)

        try:
            dst_path = location_path_on_compute(file.location, dst_compute)
            src_path = location_path_on_compute(from_location)

            if not src_storage.exists(src_path):
                logger.error(f"Cannot find file at: {from_location}")
                raise IOError(f"Cannot find file: {from_location}")

            # We need to check file existence, otherwise Django storages creates
            # a new random suffixed name rather than clobbering the existing
            # file !
            if dst_storage.exists(dst_path):
                if clobber:
                    logger.info(f"Clobbering file at {to_location}")
                    dst_storage.delete(dst_path)
                else:
                    logger.info(
                        f"A file already exists at {to_location} and clobber=False, skipping copy: {dst_path}"
                    )

            if not dst_storage.exists(dst_path):
                logger.info(f"Copying file to: {dst_compute}:{dst_path}")

                if from_location != to_location:
                    dst_storage.save(dst_path, file._file(from_location))

                    # chmod the destination to be the same as the source

                    src_mode: int = src_storage.sftp.stat(src_path).st_mode
                    dst_storage.sftp.chmod(dst_path, src_mode)

                verification_ok = verify(file, to_location, verify_on=verify_on)

                if not verification_ok:
                    message = (
                        f"File verification failed after copy ({file.id}: "
                        f"{from_location} -> {to_location}). "
                        f"Checksum for {to_location} doesn't match expected checksum: {file.checksum}"
                    )
                    if delete_failed_destination_copy:
                        dst_storage.delete(dst_path)
                        logger.info(
                            f"Deleted corrupted copy of {file.id} at {to_location}, "
                            f"copy failed verification."
                        )

                    logger.error(message)
                    raise Exception(message)

                if make_default:
                    file.location = to_location

                file.save()

        except BaseException as e:
            logger.error(
                f"Failed to copy {file.id} from {from_location} to {to_location}"
            )
            raise e

    return file


@shared_task(queue="low-priority", bind=True, track_started=True)
def copy_file_task(self, task_data=None, **kwargs):
    from ..models import File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    file_id = task_data.get("file_id")
    from_location = task_data.get("from_location", None)
    to_location = task_data.get("to_location")
    make_default = False
    clobber = task_data.get("clobber", False)
    verify_on = task_data.get("verify_on", VerifMode.CHECKSUM_IF_SET)
    deleted_failed = True

    start_time = None
    end_time = None
    try:
        file = File.objects.get(id=file_id)

        if from_location is None:
            from_location = file.location
        elif not file.locations.filter(url=from_location).exists():
            raise ValueError(f"File {file.id} does not have location: {from_location}")

        try:
            start_time = datetime.utcnow()
            file = copy_file_to(
                file,
                from_location,
                to_location,
                make_default=make_default,
                clobber=clobber,
                verify_on=verify_on,
                delete_failed_destination_copy=deleted_failed,
            )
            end_time = datetime.utcnow()
            wall_time = (end_time - start_time).total_seconds()
        except BaseException as e:
            logger.error(
                f"Failed to copy {file_id} from {from_location} to {to_location}"
            )
            raise e

        task_data.update(
            result={
                "file_id": file.id,
                "operation": "copy",
                "to": to_location,
                "from": from_location,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "walltime_seconds": wall_time,
            }
        )
    except BaseException as e:
        message = get_traceback_message(e)
        self.update_state(state=states.FAILURE, meta=message)
        raise Exception(message)

    return task_data


def add_file_replica_records(
    files: Iterable[File],
    compute_resource: Union[str, ComputeResource],
    set_as_default=False,
) -> int:
    """
    Adds a new laxy+sftp:// file location to every files in a job, given
    a ComputeResource. If set_as_default=True, the new replica location becomes the
    default location.

    NOTE: This task doesn't actually move any data - it's more intended for situations
    where data has been moved out-of-band (eg, rsynced manually, not via an
    internal Laxy task) but records in the database need to be updated.
    """

    if isinstance(compute_resource, str):
        compute_resource = ComputeResource.objects.get(id=compute_resource)

    # if isinstance(job, str):
    #     job = Job.objects.get(id=job)
    # files = job.get_files()

    new_prefix = f"laxy+sftp://{compute_resource.id}"

    n_added = 0
    with transaction.atomic():
        for f in files:
            replica_url = f"{new_prefix}/{f.fileset.job.id}/{f.full_path}"
            # try:
            loc, created = FileLocation.objects.get_or_create(file=f, url=replica_url)
            if set_as_default:
                loc.set_as_default(save=True)
            if created:
                n_added += 1
            #
            # except IntegrityError as ex:
            #     if 'unique constraint' in ex.message:
            #         pass

    return n_added


def remove_file_replica_records(
    files: QuerySet,
    compute_resource: Union[str, ComputeResource],
    allow_delete_default=False,
) -> int:
    """
    Removes the laxy+sftp:// file location for the specified ComputeResource for every
    file in a job, if there is an alternative location in existence.

    This method will raise an exception if trying to delete a FileLocation
    marked as the 'default', since this is something you probably don't want to do.
    If really want to do that, set allow_delete_default = True.

    NOTE: This task doesn't actually move any data - it's more intended for situations
    where data has been moved out-of-band (eg, rsynced manually, not via an
    internal Laxy task) but records in the database need to be updated.
    """

    if isinstance(compute_resource, str):
        compute_resource = ComputeResource.objects.get(id=compute_resource)

    n_deleted = 0
    with transaction.atomic():
        old_prefix = f"laxy+sftp://{compute_resource.id}/"
        oldlocs = FileLocation.objects.filter(
            file__in=files, url__startswith=old_prefix
        )
        # TODO: This safety check seems to be triggering when it shouldn't ??
        # if not allow_delete_default and oldlocs.filter(default=True).exists():
        #     raise ValueError(f"The provided ComputeResource ({compute_resource.id}) "
        #                      f"is used as a default location for at least some of the files in the provided QuerySet. "
        #                      f"Either set allow_delete_default = True, or ensure no files provided "
        #                      f"use this ComputeResource in their default location.")

        n_deleted = oldlocs.count()
        # NOTE: Delete on a QuerySet DOES trigger post_delete signals (eg ensure_one_default_filelocation)
        oldlocs.delete()

    return n_deleted
