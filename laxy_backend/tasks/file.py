import fnmatch
import traceback
from django.db import transaction
from typing import Sequence, Union
from datetime import datetime
from pathlib import Path
import logging
import os
from os.path import join, expanduser
import random
import time
import json
import base64
from io import BytesIO, StringIO
from copy import copy
from contextlib import closing
from django.conf import settings
from paramiko.config import SSHConfig

from celery.result import AsyncResult
from django.contrib.contenttypes.models import ContentType
from django.template import TemplateDoesNotExist
from django.template.loader import get_template, render_to_string, select_template
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (Ignore,
                               InvalidTaskError,
                               TimeLimitExceeded,
                               SoftTimeLimitExceeded)
import requests
import cgi
import backoff

from fabric.api import settings as fabsettings
from fabric.api import env as fabric_env
from fabric.api import put, run, shell_env, local, cd, show

# logging.config.fileConfig('logging_config.ini')
# logger = logging.getLogger(__name__)
from ..models import (Job, File, EventLog,
                      get_compute_resource_for_location, get_storage_class_for_location)
from ..util import get_traceback_message

logger = get_task_logger(__name__)


@shared_task(bind=True, track_started=True)
def bulk_copy_job(self, task_data=None, **kwargs):
    from ..models import File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get('job_id')
    to_location = task_data.get('new_location')

    # TODO: Complete this task - probably should use rsync, verify transfer worked (eg, rsync twice with checksums and
    # non-zero error code), then update all input_files and output_files default FileLocations in a transaction.

from urllib.parse import urlparse
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


def copy_file_to(file: File, to_location: str, make_default=False) -> File:
    with transaction.atomic():
        from_location = file.location

        # TODO: If scheme is laxy+ftp and netloc is the same between from_location and to_location,
        #       skip using storage.save and use fabric to do a 'local' copy on the ComputeResource
        #       (probably via rsync)

        storage = get_storage_class_for_location(to_location)
        new_compute = get_compute_resource_for_location(to_location)

        try:
            new_path = location_path_on_compute(file.location, new_compute)
            print(f'Copying file to: {new_path}')
            # full_path = file.full_path
            # We need to check file existence, otherwise Django storages creates a new name rather than clobbering the
            # existing file !
            if not storage.exists(new_path):
                # TODO: This is creating zero-size files ! BytesIO(file.file.read()) works, so
                #       it's something to do with the file.file filelike API ...
                storage.save(new_path, file.file)
        except BaseException as e:
            logger.error(f'Failed to copy {file.id} from {from_location} to {to_location}')
            raise e

        file.location = to_location
        if not make_default:
            file.location = from_location

        file.save()
        return file


@shared_task(bind=True, track_started=True)
def copy_file(self, task_data=None, **kwargs):
    from ..models import File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    file_id = task_data.get('file_id')
    to_location = task_data.get('new_location')
    start_time = None
    end_time = None
    try:
        file = File.objects.get(id=file_id)
        from_location = file.location
        try:
            start_time = datetime.utcnow().isoformat()
            file = copy_file_to(file, to_location)
            end_time = datetime.utcnow().isoformat()
        except BaseException as e:
            logger.error(f'Failed to copy {file_id} from {from_location} to {to_location}')
            raise e

        task_data.update(result={'file_id': file.id,
                                 'operation': 'copy',
                                 'to': to_location,
                                 'from': from_location,
                                 'start_time': start_time,
                                 'end_time': end_time})
    except BaseException as e:
        message = get_traceback_message(e)
        self.update_state(state=states.FAILURE, meta=message)
        raise Exception(message)

    return task_data
