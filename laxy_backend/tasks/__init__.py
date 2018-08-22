from pathlib import Path

import logging
import os
from os.path import join, expanduser
import random
import time
import json
import base64
from io import BytesIO
from copy import copy
from contextlib import closing
from django.conf import settings
from django.template.loader import get_template, render_to_string
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
from laxy_backend.util import laxy_sftp_url

logger = get_task_logger(__name__)


def _init_fabric_env():
    env = fabric_env
    # env.host_string = "localhost"
    # env.post = 22
    # env.user = "laxyjobrunner"
    # env.key_filename = os.expanduser("~/.ssh/id_rsa"
    # env.key = "----- BEGIN RSA PRIVATE KEY -----\n  ..etc.."
    # this adds the path of the environment running this script to the
    # fabric path. Note this is for localhost, not the remote host.
    # env.shell_env['PATH'] = '$PATH:%s:%s ' % (env.shell_env.get('PATH', ''),
    #                                           os.environ.get('PATH', ''))
    # env.warn_only = getattr(settings, 'DEBUG', False)
    env.warn_only = False
    env.use_ssh_config = False
    env.abort_on_prompts = True
    env.reject_unknown_hosts = False
    env.forward_agent = False
    env.timeout = 10
    env.command_timeout = None
    env.connection_attempts = 3
    env.keepalive = 10

    return env


@shared_task(bind=True, track_started=True)
def start_job(self, task_data=None, **kwargs):
    from ..models import Job

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    result = task_data.get('result')
    master_ip = job.compute_resource.host
    gateway = job.compute_resource.gateway_server

    webhook_notify_url = ''
    # secret = None

    environment = task_data.get('environment', {})
    job_auth_header = task_data.get('job_auth_header', '')
    # environment.update(JOB_ID=job_id)
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get('username', None)
    base_dir = job.compute_resource.extra.get('base_dir', '/tmp/')

    job_script_template_vars = dict(environment)
    job_script_template_vars['JOB_AUTH_HEADER'] = job_auth_header
    job_script = render_to_string('job_scripts/run_job.sh',
                                  context=job_script_template_vars)
    curl_headers = BytesIO(b"%s\n" % job_auth_header.encode('utf-8'))
    job_script = BytesIO(job_script.encode('utf-8'))
    config_json = BytesIO(json.dumps(job.params).encode('utf-8'))

    remote_id = None
    message = "Failure, without exception."
    try:
        with fabsettings(gateway=gateway,
                         host_string=master_ip,
                         user=remote_username,
                         key=private_key,
                         # key_filename=expanduser("~/.ssh/id_rsa"),
                         ):
            working_dir = os.path.join(base_dir, job_id)
            input_dir = join(working_dir, 'input')
            output_dir = join(working_dir, 'output')
            job_script_path = join(input_dir, 'run_job.sh')
            for d in [working_dir, input_dir, output_dir]:
                result = run(f'mkdir -p {d} && chmod 700 {d}')
            result = put(job_script,
                         job_script_path,
                         mode=0o700)
            result = put(curl_headers,
                         join(working_dir, '.private_request_headers'),
                         mode=0o600)
            result = put(config_json,
                         join(input_dir, 'pipeline_config.json'),
                         mode=0o600)
            with cd(working_dir):
                with shell_env(**environment):
                    result = run(f"nohup bash -l -c '"
                                 f"{job_script_path} & "
                                 f"echo $! >job.pid"
                                 f"' >output/run_job.out")
                with shell_env(**environment):
                    remote_id = run(str("cat job.pid"))

        succeeded = result.succeeded
    except BaseException as e:
        succeeded = False
        if hasattr(e, 'message'):
            message = e.message
        else:
            message = repr(e)

    if not succeeded and job.compute_resource.disposable:
        job.compute_resource.dispose()

    job_status = Job.STATUS_RUNNING if succeeded else Job.STATUS_FAILED
    job = Job.objects.get(id=job_id)
    job.status = job_status
    job.remote_id = remote_id
    job.save()

    # if webhook_notify_url:
    #     job_status = Job.STATUS_STARTING if succeeded else Job.STATUS_FAILED
    #     resp = request_with_retries(
    #         'PATCH', callback_url,
    #         json={'status': job_status},
    #         headers={'Authorization': secret},
    #     )

    if not succeeded:
        self.update_state(state=states.FAILURE, meta=message)
        raise Exception(message)
        # raise Ignore()

    task_data.update(result=result)

    return task_data


def remote_list_files(path='.'):
    """
    Recursively list files relative to the specified path.
    Intended to be called within a Fabric context.

    :param path: A path (absolute or relative to cwd)
    :type path: str
    :return: A list of relative paths.
    :rtype: List[str]
    """
    # -L ensures symlinks are followed and output as filenames too
    lslines = run(f"find -L {path} -mindepth 1 -type f -printf '%P\n'")
    if not lslines.succeeded:
        raise Exception("Failed to list remote files: %s" % lslines)
    filepaths = lslines.splitlines()
    filepaths = [f for f in filepaths if f.strip()]
    return filepaths


@shared_task(bind=True, track_started=True)
def index_remote_files(self, task_data=None, **kwargs):
    from ..models import Job, File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    result = task_data.get('result')
    clobber = task_data.get('clobber', False)
    master_ip = job.compute_resource.host
    gateway = job.compute_resource.gateway_server

    webhook_notify_url = ''
    # secret = None

    environment = task_data.get('environment', {})
    # environment.update(JOB_ID=job_id)
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get('username', None)
    base_dir = job.compute_resource.extra.get('base_dir', '/tmp/')

    compute_id = job.compute_resource.id
    message = "No message."

    def create_update_file_objects(remote_path,
                                   fileset=None,
                                   prefix_path='',
                                   location_base=''):
        """
        Returns a list of (unsaved) File objects from a recursive 'find'
        of a remote directory. If a file of the same path exists in the FileSet,
        update the file object location (if unset) rather than create a new one.

        :param fileset:
        :type fileset:
        :param prefix_path:
        :type prefix_path:
        :param remote_path: Path on the remote server.
        :type remote_path: str
        :param location_base: Prefix of location URL (eg sftp://127.0.0.1/XxX/)
        :type location_base: str
        :return: A list of File objects
        :rtype: List[File]
        """

        with cd(remote_path):
            filepaths = remote_list_files('.')
            urls = [
                (f'{location_base}/{fpath}', fpath)
                for fpath in filepaths
            ]

            file_objs = []
            for location, filepath in urls:
                fname = Path(filepath).name
                fpath = Path(prefix_path) / Path(filepath).parent

                if fileset:
                    f = fileset.get_file_by_path(
                        Path(fpath) / Path(fname))

                if not f:
                    f = File(location=location,
                             owner=job.owner,
                             name=fname,
                             path=fpath)
                elif not f.location:
                    f.location = location
                    f.owner = job.owner

                file_objs.append(f)

        return file_objs

    try:
        with fabsettings(gateway=gateway,
                         host_string=master_ip,
                         user=remote_username,
                         key=private_key,
                         # key_filename=expanduser("~/.ssh/id_rsa"),
                         ):
            working_dir = os.path.join(base_dir, job_id)
            input_dir = os.path.join(working_dir, 'input')
            output_dir = os.path.join(working_dir, 'output')

            output_files = create_update_file_objects(
                output_dir,
                fileset=job.output_files,
                prefix_path='output',
                location_base=laxy_sftp_url(job, 'output'),
            )
            job.output_files.path = 'output'

            if clobber:
                job.output_files.remove(job.output_files, delete=True)

            job.output_files.add(output_files)

            # TODO: This should really be done at job start, or once input data
            #       has been staged on the compute node.
            input_files = create_update_file_objects(
                input_dir,
                fileset=job.input_files,
                prefix_path='input',
                location_base=laxy_sftp_url(job, 'input')
            )
            job.input_files.path = 'input'

            if clobber:
                job.input_files.remove(job.input_files, delete=True)

            job.input_files.add(input_files)

        succeeded = True
    except BaseException as e:
        succeeded = False
        if hasattr(e, 'message'):
            message = e.message

        self.update_state(state=states.FAILURE, meta=message)
        raise e

    # job_status = Job.STATUS_RUNNING if succeeded else Job.STATUS_FAILED
    # job = Job.objects.get(id=job_id)
    # job.status = job_status
    # job.save()

    # if not succeeded:
    #     self.update_state(state=states.FAILURE, meta=message)
    #     raise Exception(message)
    #     # raise Ignore()

    task_data.update(result=result)

    return task_data


@shared_task(bind=True, track_started=True)
def poll_jobs(self, task_data=None, **kwargs):
    from ..models import Job
    running = Job.objects.filter(status=Job.STATUS_RUNNING)
    for job in running:
        poll_job_ps.apply_async(args=(dict(job_id=job.id),))


@shared_task(bind=True, track_started=True)
def poll_job_ps(self, task_data=None, **kwargs):
    from ..models import Job

    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    master_ip = job.compute_resource.host
    gateway = job.compute_resource.gateway_server
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get('username', None)

    message = "No message."
    try:
        with fabsettings(gateway=gateway,
                         host_string=master_ip,
                         user=remote_username,
                         key=private_key):
            with shell_env():
                result = run(f"ps - u {remote_username} -o pid | "
                             f"tr -d ' ' | "
                             f"grep '^{job.remote_id}$'")
                job_is_not_running = not result.succeeded

    except BaseException as e:
        if hasattr(e, 'message'):
            message = e.message

        self.update_state(state=states.FAILURE, meta=message)
        raise e

    # grab the Job from the database again to minimise race condition
    # where the status updated while we are running ssh'ing and running 'ps'
    job = Job.objects.get(id=job_id)
    if not job.done and job_is_not_running:
        job.status = Job.STATUS_FAILED
        job.save()

        index_remote_files.apply_async(args=(dict(job_id=job_id),))

    task_data.update(result=result)

    return task_data
