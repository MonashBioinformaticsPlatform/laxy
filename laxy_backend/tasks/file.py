import fnmatch
import traceback
import shlex
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

from django.db import transaction
from django.conf import settings

from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (Ignore,
                               InvalidTaskError,
                               TimeLimitExceeded,
                               SoftTimeLimitExceeded)

from .job import add_file_replica_records, remove_file_replica_records
from ..models import (Job,
                      File,
                      FileLocation,
                      EventLog,
                      get_compute_resource_for_location,
                      get_storage_class_for_location, ComputeResource, get_primary_compute_location_for_files,
                      job_path_on_compute)
from ..util import get_traceback_message

logger = get_task_logger(__name__)


def do_pipe_copy(job: Job,
                 src_compute: ComputeResource,
                 dst_compute: ComputeResource):

    # This opens two SSH connections, one to the source and one to the destination and pipes data via tar.
    # The network path is like:
    #   clientA -> laxy_backend(celery worker) -> clientB

    src_path = job_path_on_compute(job, src_compute)
    dst_path = job_path_on_compute(job, dst_compute)
    bytes_transferred = 0

    with src_compute.ssh_client(compress=False) as src_client:
        cmd_src = f'tar -chzf - --directory "{src_path}" .'
        print(cmd_src)
        # NO: Setting bufsize seems to result in an incomplete transfer (but ideally we'd like to tune the bufsize
        #       for performance)
        src_stdin, src_stdout, src_stderr, src_chan = src_client.exec_command_channel(cmd_src)  #, bufsize=buffer_size)
        with dst_compute.ssh_client(compress=False) as dst_client:
            cmd_dst = f'mkdir -p "{dst_path}" && tar -xzf - --directory "{dst_path}"'
            print(cmd_dst)
            dst_stdin, dst_stdout, dst_stderr, dst_chan = dst_client.exec_command_channel(cmd_dst)  #, bufsize=buffer_size)
            for chunk in src_stdout:
                dst_stdin.write(chunk)
                bytes_transferred += len(chunk)

            src_stdout.close()
            dst_stdin.close()

    return bytes_transferred, src_chan.recv_exit_status(), dst_chan.recv_exit_status()


def delete_remote_files(job, compute_resource):
    job_path = job_path_on_compute(job, compute_resource)
    out = ''
    with compute_resource.ssh_client(compress=False) as ssh_client:
        job_path = shlex.quote(job_path)
        # Sanity check the path since we are doing rm -rf
        if job.id not in job_path:
            raise ValueError(f"Aborting delete_remote_files: job path "
                             f"{job_path} on {compute_resource.id} looks suspicious.")

        cmd_src = f'find {job_path} -type f | wc -l && rm -rf {job_path}'
        print(cmd_src)
        (stdin, stdout, stderr) = ssh_client.exec_command(cmd_src)
        if not stdout.closed:
            out = stdout.read().decode()
        [_.close() for _ in (stdin, stdout, stderr)]

    return out


@shared_task(bind=True, track_started=True)
def bulk_move_job_task(self, task_data=None, **kwargs):
    """
    Moves all files in a job from one ComputeResource to another, tunneling via the
    laxy_backend (celery worker). Verifies any files at the destination that have a
    File.checksum set. Adds a new location record for each file, setting the copy
    as the new default, then removes the old location record. Finally, deletes the job
    directory at the source.

    This task is really only intended as an interim solution until per-file
    django-storages based transfers are made more reliable.

    Design and Caveats
    -----------------
    This task won't work as properly for Jobs where files are not all stored on
    the same SSH-accessible ComputeResource (eg, if some files are on object storage).

    Under the hood it opens SSH connections to the source (A) and destination (B) hosts and
    uses `tar` with Unix pipes. Traffic tunnels A->celery worker->B, there is no direct traffic
    between A and B. While `rsync` would be more desirable, this design was
    chosen since all the 3-way rsync methods I could find required the source host to have
    direct SSH access to the destination, either via authorized_keys, or using ssh-agent. This
    was a potential security issue in the case where Laxy is copying files between hosts that
    don't trust each other (eg, if user A adds their own ComputeResource which they control, but
    Laxy wants to transfer files to an archival service that only Laxy controls).

    :param self:
    :type self:
    :param task_data:
    :type task_data:
    :param kwargs:
    :type kwargs:
    :return:
    :rtype:
    """
    if task_data is None:
        raise InvalidTaskError("task_data is None")

    message = None
    try:
        job_id = task_data.get('job_id')
        dst_compute_id = task_data.get('dst_compute_id')

        job = Job.objects.get(id=job_id)
        dst_compute = ComputeResource.objects.get(id=dst_compute_id)
        # src_compute = get_primary_compute_location_for_files(job.get_files())
        src_compute = job.compute_resource
        task_data['src_compute'] = src_compute.id

        # Currently this task only works for moving from the original job location
        # to somewhere else (eg an archival location). If we aren't in the original
        # location, assume we've moved already, do nothing.
        # stored_at = get_primary_compute_location_for_files(job.get_files())
        # if stored_at.id != src_compute.id:
        #     result = 'no_move_required'
        #     return task_data

        n_added = 0
        n_removed = 0
        bytes_transferred = 0
        result = {}
        try:
            xfer_started_at = datetime.now()
            # if stored_at.id != dst_compute.id:
            #    bytes_transferred = do_pipe_copy(job, src_compute, dst_compute)
            bytes_transferred, src_exitcode, dst_exitcode = do_pipe_copy(job, src_compute, dst_compute)
            xfer_finished_at = datetime.now()
            xfer_walltime = (xfer_finished_at - xfer_started_at).total_seconds()
            kbps = (bytes_transferred / 1000) / xfer_walltime
            result['do_pipe_copy'] = {'started_time': xfer_started_at.isoformat(),
                                      'finished_time': xfer_finished_at.isoformat(),
                                      'walltime_seconds': xfer_walltime,
                                      'rate_kbps': kbps,
                                      'src_exitcode': src_exitcode,
                                      'dst_exitcode': dst_exitcode}
        except BaseException as ex:
            logger.error(f'Failed to copy {job_id} from {src_compute.id} to {dst_compute.id} '
                         f'(bulk_move_job_task:do_pipe_copy)')
            message = get_traceback_message(ex)
            raise ex

        try:
            # if stored_at.id != dst_compute.id:
            #     n_added = add_file_replica_records(job.get_files(), dst_compute, set_as_default=True)
            n_added = add_file_replica_records(job.get_files(), dst_compute, set_as_default=True)
            result['add_file_replica_records'] = n_added
        except BaseException as ex:
            logger.error(f'Failed add file replica records for {job_id}, new ComputeResource {dst_compute.id} '
                         f'(bulk_move_job_task:add_file_replica_records)')
            message = get_traceback_message(ex)
            raise ex

        try:
            result['verify'] = {'success': False, 'failed_locations': []}
            for f in job.get_files():
                exc_name = None
                try:
                    ok = verify(f, f.location)
                except IOError as ex:
                    ok = False
                    exc_name = type(ex).__name__
                if not ok and f.checksum:
                    detail = {'file': f.id,
                              'location': f.location,
                              'exception': exc_name}
                    result['verify']['failed_locations'].append(detail)
                    raise Exception('File verification failed:' + str(detail))

            result['verify']['success'] = len(result['verify']['failed_locations']) == 0

        except BaseException as ex:
            logger.error(f'Unable to verify copied files for {job_id} at '
                         f'destination {dst_compute.id} not deleting source copy. '
                         f'(bulk_move_job_task:verify_task)')
            message = get_traceback_message(ex)
            raise ex

        try:
            n_removed = remove_file_replica_records(job.get_files(), src_compute)
            result['remove_file_replica_records'] = n_removed
        except BaseException as ex:
            logger.error(f'Failed remove file replica records for {job_id}, old ComputeResource {src_compute.id} '
                         f'(bulk_move_job_task:remove_file_replica_records)')
            message = get_traceback_message(ex)
            raise ex

        try:
            delete_stdout = delete_remote_files(job, src_compute)
            result['delete_remote_files'] = delete_stdout
        except BaseException as ex:
            logger.error(f'Failed delete remote files for {job_id}, on ComputeResource {src_compute.id} '
                         f'(bulk_move_job_task:delete_remote_files)')
            message = get_traceback_message(ex)
            raise ex

        result['success'] = True
        task_data['result'] = result
        task_succeeded = True

    except BaseException as ex:
        task_succeeded = False
        exc_type = type(ex).__name__
        if message is None:
            message = get_traceback_message(ex)
        print(message)

    if not task_succeeded:
        # self.update_state(state=states.FAILURE,
        #                   meta={'exc_type': exc_type,
        #                         'exc_message': message.split('\n'),
        #                         'result': result})
        raise Exception('\n'.join([message, str(result)]))

    return task_data


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
    with BufferedReader(filelike, buffer_size=chunk_size * 128).raw as fh:
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
