import fnmatch
import shlex
import traceback
from django.db import transaction
from typing import Sequence, Union, Iterable
from datetime import datetime, timedelta
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
from django.db.models import QuerySet
from django.db import IntegrityError

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
from ..models import Job, File, EventLog, ComputeResource, FileLocation, get_primary_compute_location_for_files, \
    job_path_on_compute, get_compute_resources_for_files
from ..util import laxy_sftp_url, get_traceback_message

logger = get_task_logger(__name__)

# For debugging - paramiko logs to seperate file
# import paramiko
# logging.getLogger("paramiko").setLevel(logging.DEBUG)
# paramiko.util.log_to_file("/app/paramiko.log", level="DEBUG")


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
    env.load_ssh_configs = False
    # ssh_config = SSHConfig().parse(
    #     [
    #         "Host *\n",
    #         "    PasswordAuthentication no\n"
    #         "    PubkeyAuthentication yes\n"
    #         "    PreferredAuthentications publickey\n"
    #         "    IdentitiesOnly yes\n"
    #     ]
    # )
    # env.ssh_config = ssh_config
    env.abort_on_prompts = True
    env.reject_unknown_hosts = False
    env.forward_agent = False
    env.timeout = 10
    env.command_timeout = None
    env.connection_attempts = 3
    env.keepalive = 10

    return env


def get_template_files(must_contain='/job_scripts/'):
    from django.conf import settings
    from django.template.loaders.app_directories import get_app_template_dirs
    import os

    template_dir_list = list(get_app_template_dirs('templates'))

    # Or just for this app ...
    #       from django.apps import apps
    #       app = apps.get_app_config(app_name)
    #       template_dir = os.path.abspath(os.path.join(app.path, 'templates'))

    template_list = []
    for template_dir in (template_dir_list + settings.TEMPLATES[0]['DIRS']):
        for base_dir, dirnames, filenames in os.walk(template_dir):
            for filename in filenames:
                template_list.append(os.path.join(base_dir, filename))

    return [p for p in template_list if must_contain in p]


@shared_task(bind=True, track_started=True)
def start_job(self, task_data=None, **kwargs):
    from ..models import Job

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    result = task_data.get('result')
    host = job.compute_resource.host
    gateway = job.compute_resource.gateway_server

    webhook_notify_url = ''
    # secret = None

    environment = task_data.get('environment', {})
    job_auth_header = task_data.get('job_auth_header', '')
    # environment.update(JOB_ID=job_id)
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get('username', None)

    pipeline_name = job.params.get('pipeline')
    pipeline_version = job.params.get('params', {}).get('pipeline_version', 'default')

    def find_job_file(script: str) -> Union[str, None]:
        base = f'job_scripts/{pipeline_name}'
        options = [f'{base}/{pipeline_version}/{script}',
                   f'{base}/default/{script}']
        try:
            template = select_template(options)
            return template.origin.name
        except TemplateDoesNotExist:
            logger.warning(f"Unable to find job template file in: {str(options)}")
            return None

        # for fpath in options:
        #     # if os.path.exists(fpath):
        #     #    return fpath
        #     try:
        #         template = get_template(fpath)
        #     except TemplateDoesNotExist:
        #         continue

        # raise IOError(f"Unable to find job template file: {script}")

    job_script_template_vars = dict(environment)

    def template_filelike(fpath):
        return BytesIO(
            render_to_string(fpath, context=job_script_template_vars).encode('utf-8'))

    config_json = BytesIO(json.dumps(job.params).encode('utf-8'))
    job_script_template_vars['JOB_AUTH_HEADER'] = job_auth_header
    curl_headers = BytesIO(b"%s\n" % job_auth_header.encode('utf-8'))

    # TODO: This should be refactored to just grab EVERY file recursively in job_scripts/{pipeline_name}/default/,
    #       then overwriting / overriding with any files in job_scripts/{pipeline_name}/{pipeline_version}.
    #       Treat every file as it as a template (or maybe only if it has a .j2 extension ?), and copy it
    #       to the equivalent relative path on the compute node (eg input/ and output/).
    #       Possibly using the get_template_files() function. But things might be easier at this point if
    #       we just ignored the Django template system and just worked with os.walk and the laxy_backend/templates path.

    job_script = template_filelike(find_job_file('input/run_job.sh'))
    add_to_manifest_script = template_filelike(find_job_file('input/add_to_manifest.py'))
    kill_script = template_filelike(find_job_file('kill_job.sh'))

    # From: conda list --explicit >conda_environment_explicit.txt
    conda_env_template = find_job_file('input/conda_environment_explicit.txt')
    if not conda_env_template:
        # From: conda env export >../conda_environment.yml
        find_job_file('input/conda_environment.yml')

    conda_env = template_filelike(find_job_file('input/conda_environment.yml'))

    remote_id = None
    message = "Failure, without exception."
    try:
        with fabsettings(gateway=gateway,
                         host_string=host,
                         user=remote_username,
                         key=private_key,
                         # key_filename=expanduser("~/.ssh/id_rsa"),
                         ):
            working_dir = job.abs_path_on_compute
            input_dir = join(working_dir, 'input')
            output_dir = join(working_dir, 'output')
            job_script_path = join(input_dir, 'run_job.sh')
            kill_script_path = join(working_dir, 'kill_job.sh')
            conda_env_path = join(input_dir, 'conda_environment.yml')
            for d in [working_dir, input_dir, output_dir]:
                result = run(f'mkdir -p {d} && chmod 700 {d}')
            result = put(job_script,
                         job_script_path,
                         mode=0o700)
            result = put(add_to_manifest_script,
                         join(input_dir, 'add_to_manifest.py'),
                         mode=0o700)
            result = put(kill_script,
                         kill_script_path,
                         mode=0o700)
            result = put(conda_env,
                         conda_env_path,
                         mode=0o600)
            result = put(curl_headers,
                         join(working_dir, '.private_request_headers'),
                         mode=0o600)
            result = put(config_json,
                         join(input_dir, 'pipeline_config.json'),
                         mode=0o600)
            with cd(working_dir):
                with shell_env(**environment):
                    # NOTE: We can't sbatch the run_job.sh script due to
                    #       the local aria2c RPC daemon launched by laxydl
                    #       In the future, we may have a DataTransferHost where
                    #       the data staging steps run, then we could launch
                    #       run_job.sh via sbatch.
                    # if job.compute_resource.queue_type == 'slurm':
                    #     result = run(f"sbatch --parsable "
                    #                  f'--job-name="laxy:{job_id}" '
                    #                  f"--output output/run_job.out "
                    #                  f"{job_script_path} "
                    #                  f" >>slurm.jids")
                    #     remote_id = run(str("head -1 slurm.jids"))

                    # The job script is always run locally on the compute
                    # node (not sbatched), but will itself send jobs
                    # to the queue.
                    result = run(f"nohup bash -l -c '"
                                 f"{job_script_path} & "
                                 f"echo $! >>job.pids"
                                 f"' >output/run_job.out")
                    remote_id = run(str("head -1 job.pids"))

        succeeded = result.succeeded
    except BaseException as e:
        succeeded = False
        message = get_traceback_message(e)

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
    # path = shlex.quote(path)
    # -L ensures symlinks are followed and output as filenames too
    lslines = run(f"find -L {path} -mindepth 1 -type f -printf '%P\n'")
    if not lslines.succeeded:
        raise Exception("Failed to list remote files: %s" % lslines)
    filepaths = lslines.splitlines()
    filepaths = [f for f in filepaths if f.strip()]
    return filepaths


@shared_task(bind=True, track_started=True)
def set_job_status(self, task_data=None, **kwargs):
    from ..models import Job, File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get('job_id')
    status = task_data.get('status')
    with transaction.atomic():
        job = Job.objects.get(id=job_id)
        job.status = status
        job.save()

    if (job.done and
            job.compute_resource and
            job.compute_resource.disposable and
            not job.compute_resource.running_jobs()):
        job.compute_resource.dispose()

    return task_data


@shared_task(bind=True, track_started=True)
def index_remote_files(self, task_data=None, **kwargs):
    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    clobber = task_data.get('clobber', False)

    compute_resource = job.compute_resource
    if compute_resource is not None:
        host = compute_resource.host
        gateway = compute_resource.gateway_server
    else:
        logger.info(f"Not indexing files for {job_id}, no compute_resource.")
        return task_data

    job.log_event('JOB_INFO', 'Indexing all files (backend task)')

    environment = task_data.get('environment', {})
    # environment.update(JOB_ID=job_id)
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get('username', None)

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
        if 'results' not in task_data:
            task_data['results'] = {}

        with fabsettings(gateway=gateway,
                         host_string=host,
                         user=remote_username,
                         key=private_key,
                         # key_filename=expanduser("~/.ssh/id_rsa"),
                         ):
            working_dir = job.abs_path_on_compute
            input_dir = os.path.join(working_dir, 'input')
            output_dir = os.path.join(working_dir, 'output')

            output_files = create_update_file_objects(
                output_dir,
                fileset=job.output_files,
                prefix_path='output',
                location_base=laxy_sftp_url(job, 'output'),
            )
            job.output_files.path = 'output'
            job.output_files.owner = job.owner

            if clobber:
                job.output_files.remove(job.output_files, delete=True)

            job.output_files.add(output_files)
            task_data['results']['output_files_indexed'] = len(output_files)

            # TODO: This should really be done at job start, or once input data
            #       has been staged on the compute node.
            input_files = create_update_file_objects(
                input_dir,
                fileset=job.input_files,
                prefix_path='input',
                location_base=laxy_sftp_url(job, 'input')
            )
            job.input_files.path = 'input'
            job.input_files.owner = job.owner

            if clobber:
                job.input_files.remove(job.input_files, delete=True)

            job.input_files.add(input_files)
            task_data['results']['input_files_indexed'] = len(input_files)

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

    return task_data


@shared_task(bind=True)
def _index_remote_files_task_err_handler(self, uuid, job_id=None):
    logger.info(f'_index_files_task_err_handler: failed task: {uuid}, job_id: {job_id}')
    result = AsyncResult(uuid)

    job = Job.objects.get(id=job_id)
    job.status = Job.STATUS_FAILED
    job.save()

    eventlog = job.log_event('JOB_FINALIZE_ERROR', '',
                             extra={'task_id': uuid,
                                    # 'exception': exc,
                                    'traceback': result.traceback})
    message = f'Failed to index files and finalize job status (EventLog ID: {eventlog.id})'
    eventlog.message = message
    eventlog.save()

    if job.compute_resource and job.compute_resource.disposable:
        job.compute_resource.dispose()


@shared_task(bind=True, track_started=True)
def poll_jobs(self, task_data=None, **kwargs):
    from ..models import Job
    running = Job.objects.filter(status=Job.STATUS_RUNNING)
    for job in running:
        poll_job_ps.apply_async(args=(dict(job_id=job.id),))


# TODO: Instead of calling 'ps' or 'squeue' directly,
# use the `kill_job.sh check` functionality
@shared_task(bind=True, track_started=True)
def poll_job_ps(self, task_data=None, **kwargs):
    from ..models import Job

    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    host = job.compute_resource.host
    gateway = job.compute_resource.gateway_server
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get('username', None)

    message = "No message."
    try:
        with fabsettings(gateway=gateway,
                         host_string=host,
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


@shared_task(bind=True, track_started=True)
def kill_remote_job(self, task_data=None, **kwargs):
    from ..models import Job

    _init_fabric_env()

    environment = task_data.get('environment', {})
    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    host = job.compute_resource.host
    gateway = job.compute_resource.gateway_server
    queue_type = job.compute_resource.queue_type
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get('username', None)

    working_dir = job.abs_path_on_compute
    kill_script_path = join(working_dir, 'kill_job.sh')

    message = "No message."
    try:
        with fabsettings(gateway=gateway,
                         host_string=host,
                         user=remote_username,
                         key=private_key):
            with cd(working_dir):
                with shell_env(**environment):
                    # if queue_type == 'slurm':
                    #     result = run(f"scancel {job.remote_id}")
                    # else:
                    #     result = run(f"kill {job.remote_id}")

                    result = run(f"{kill_script_path} kill")
                    job_killed = result.succeeded

    except BaseException as e:
        if hasattr(e, 'message'):
            message = e.message

        self.update_state(state=states.FAILURE, meta=message)
        raise e

    task_data.update(result=result)

    return task_data


@shared_task(bind=True, track_started=True)
def estimate_job_tarball_size(self, task_data=None, **kwargs):
    if task_data is None:
        raise InvalidTaskError("task_data is None")

    from ..models import Job

    _init_fabric_env()

    environment = task_data.get('environment', {})
    job_id = task_data.get('job_id')
    job = Job.objects.get(id=job_id)
    # stored_at = get_primary_compute_location_for_files(job.get_files())
    compute_locs = [c for c in get_compute_resources_for_files(job.get_files()) if c is not None]
    stored_at = compute_locs.pop()
    host = stored_at.host
    gateway = stored_at.gateway_server
    queue_type = stored_at.queue_type
    private_key = stored_at.private_key
    remote_username = stored_at.extra.get('username', None)

    job_path = job_path_on_compute(job, stored_at)
    # job_path = job.abs_path_on_compute

    message = "No message."
    task_result = dict()
    try:
        with fabsettings(gateway=gateway,
                         host_string=host,
                         user=remote_username,
                         key=private_key):
            with cd(job_path):
                with shell_env(**environment):
                    # if queue_type == 'slurm':
                    #     result = run(f"scancel {job.remote_id}")
                    # else:
                    #     result = run(f"kill {job.remote_id}")

                    # NOTE: If running tar -chzf is too slow / too much extra I/O load,
                    #       we could use the placeholder heuristic of
                    #       f`du -bc --max-depth=0 "{job_path}"` * 0.66 for RNAsik runs,
                    #       stored in job metadata. Or add proper sizes to every File.metdata
                    #       and derive it from a query.
                    # We run as 'nice' since this is considered low priority

                    result = run(f'nice tar -chzf - --directory "{job_path}" . | nice wc --bytes')
                    tries = 0
                    while result.succeeded and \
                            'file changed as we read it' in result.stdout.strip().lower() and \
                            tries <= 3:
                        result = run(f'nice tar -chzf - --directory "{job_path}" . | nice wc --bytes')
                        tries += 1

                    if result.succeeded:
                        if 'file changed as we read it' in result.stdout.strip().lower():
                            raise Exception(f"Files continue to change while calculating tarball size for "
                                            f"Job: {job.id}")

                        tarball_size = int(result.stdout.strip())
                        with transaction.atomic():
                            job = Job.objects.get(id=job_id)
                            job.params['tarball_size'] = tarball_size
                            job.save(update_fields=['params', 'modified_time'])

                        task_result['tarball_size'] = tarball_size
                    else:
                        task_result['stdout'] = result.stdout.strip()
                        task_result['stderr'] = result.stderr.strip()

    except BaseException as e:
        message = get_traceback_message(e)

        self.update_state(state=states.FAILURE, meta=message)
        raise e

    task_data.update(result=task_result)

    return task_data


# TODO: This function is very pipeline specific (RNAsik) - we need to refactor
#       to take the pipeline into account (eg based on name in Job.params.params.pipeline)
#       The various variables/rules for this function could also be declarative and
#       stored on a new PipelineConfig object.
#       IDEA: Maybe the behaviour should change so that every job has it's own cleanup script
#       that is run on expiry. Or, during the File.type_tag tagging / manifest-md5.csv phase,
#       also tag files for future expiry (explicitly, or via adding an 'expires' type_tag
#       This better acheives the goal of keeping pipeline specific stuff out of the backend and
#       pushing it to the 'run scripts'.
def file_should_be_deleted(ff: File, max_size=200):
    """
    Returns True if a File meets the criteria to be deleted (eg based on size, age, filename, type_tags).

    :param ff: The File instance.
    :type ff: File
    :param max_size: Max file size in MB (megibytes)
    :type max_size: int
    :return: True if File should be deleted
    :rtype: bool
    """
    extension = Path(ff.name).suffix
    MB = 1024 * 1024
    whitelisted_extensions = ['.txt', '.html', '.log']
    whitelisted_paths = ['**/sikRun/multiqc_data/**',
                         '**/sikRun/fastqcReport/**',
                         '**/sikRun/countFiles/**',
                         '**/sikRun/logs/**']
    whitelisted_type_tags = ['report', 'counts', 'degust']
    always_delete_extensions = ['.tmp', '.bam', '.bai', '.bw', '.bedGraph']
    always_delete_paths = ['**/sikRun/refFiles/**',
                           'input/*.fastq.gz',
                           'input/*.fastq',
                           'input/*.fq.gz'
                           'input/**/*.fastq.gz',
                           'input/**/*.fastq',
                           'input/**/*.fq.gz']

    if extension in always_delete_extensions:
        return True

    has_always_delete_path = any([fnmatch.filter([ff.full_path], pattern)
                                  for pattern in always_delete_paths])
    if has_always_delete_path:
        return True

    if ff.size is not None:
        is_large_file = (ff.size / MB) > max_size
    else:
        logger.warning(f"Cannot determine size of file {ff.id} (file_should_be_deleted). "
                       f"Erring on the side of caution and regarding this file as 'small', but be warned - "
                       f"if it's large it may hang around even though we'd rather it expired.")
        is_large_file = False

    has_whitelisted_path = any([fnmatch.filter([ff.full_path], pattern)
                                for pattern in whitelisted_paths])
    has_whitelisted_tag = any([tag in whitelisted_type_tags
                               for tag in ff.type_tags])
    return ((not ff.deleted) and
            is_large_file and
            (extension not in whitelisted_extensions) and
            (not has_whitelisted_tag) and
            (not has_whitelisted_path))


@shared_task(bind=True, track_started=True)
def expire_old_job(self, task_data=None, **kwargs):
    from ..models import Job, File
    _init_fabric_env()

    seconds_in_day = 60 * 60 * 24
    ttl = task_data.get('ttl', 30 * seconds_in_day)
    MB = 1024 * 1024

    environment = task_data.get('environment', {})
    job_id = task_data.get('job_id')
    result = {"deleted_count": 0}
    job = Job.objects.get(id=job_id)

    # def _delete_file(f):
    #     # Just an example of an alternative using fabric ...
    #     # fabsettings and shell_env should be outside this function
    #     # rather than initiating ssh connection for every call
    #     with fabsettings(gateway=gateway,
    #                      host_string=host,
    #                      user=remote_username,
    #                      key=private_key,
    #                      # key_filename=expanduser("~/.ssh/id_rsa"),
    #                      ):
    #         with shell_env(**environment):
    #             run(f"rm {f._abs_path_on_compute()}")

    # We could also use 'find' via fabric to remove files based on mtime/ctime/size ... however
    # we would need to lookup each File record based on path and update f.deleted_time
    # ttl_mins = ttl / 60
    # Find large files based on filesystem mtime
    # file_paths = run(f"find {working_dir} -type f -size +{max_size}M -mtime {ttl_mins}").splitlines()
    # Delete large files based on filesystem mtime
    # deleted_paths = run(f"find {working_dir} -type f -size +{max_size}M -mtime {ttl_mins} -delete").splitlines()

    # Use modified_time instead ?
    old_files = job.get_files().filter(created_time__lt=datetime.now() - timedelta(seconds=ttl)).all()
    message = "No message."
    try:
        count = 0
        for f in old_files:
            try:
                if file_should_be_deleted(f):
                    if f.size is not None:
                        logger.info(f"Deleting {job.id} {f.full_path} ({f.size / MB:.1f}MB)")
                    try:
                        # NOTE: There are temporary states where a file will fail to delete (network outage),
                        #       and permanent states where deletion will fail (ComputeResource no longer exists).
                        #       A job isn't marked as expired until we've successfully deleted the files that should
                        #       be deleted - but we need a way to decide that after many attempts over a reasonable
                        #       time, a file can be marked as deleted because we can't access the storage backend.
                        f.delete_file()
                        count += 1
                    except NotImplementedError:
                        logger.warning(f"Unable to delete {job.id} {f.full_path} "
                                       f"(NotImplementedError for this file location)")
                    except FileNotFoundError as ex:
                        logger.info(f"File is missing on backend storage: {job.id} {f.full_path} - marking as expired")
                        f.deleted_time = datetime.now()
                        f.save()

            except BaseException as ex:
                # If any file can't be deleted for unknown reasons, ensure we don't mark the job as expired by
                # raising an exception before that happens. This way rhe scheduled task will try again later.
                logger.error(f"Unable to delete File {f.id} in Job {job.id}:", get_traceback_message(ex))
                raise ex

        job.expired = True
        job.save()
        result = {"deleted_count": count}

        try:
            if count > 0:
                r = estimate_job_tarball_size.apply_async(args=(dict(job_id=job.id,),))
                if r.failed():
                    raise r.result
        except BaseException as ex:
            logger.error(f'Failed to start estimate_job_tarball_size task after expiring Job ({job.id}) [{get_traceback_message(ex)}]')
            pass

        try:
            job.log_event('JOB_INFO', 'Job expired, some files may be unavailable.')
        except BaseException:
            # EventLogs are nice but optional, if this fails just forge ahead
            pass

    except BaseException as e:
        message = get_traceback_message(e)

        self.update_state(state=states.FAILURE, meta=message)
        raise e

    task_data.update(result=result)

    return task_data


@shared_task(bind=True, track_started=True)
def expire_old_jobs(self, task_data=None, *kwargs):
    expiring_jobs = Job.objects.filter(
        expired=False, expiry_time__lte=datetime.now()).exclude(
        expiry_time__isnull=True).exclude(
        status=Job.STATUS_RUNNING).order_by('-expiry_time')
    for job in expiring_jobs:
        logging.info(f"Expiring job: {job.id}")
        expire_old_job.s(task_data=dict(job_id=job.id)).apply_async()


def add_file_replica_records(files: Iterable[File],
                             compute_resource: Union[str, ComputeResource],
                             set_as_default=False) -> int:
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

    new_prefix = f'laxy+sftp://{compute_resource.id}'

    n_added = 0
    with transaction.atomic():
        for f in files:
            replica_url = f'{new_prefix}/{f.fileset.job.id}/{f.full_path}'
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


def remove_file_replica_records(files: QuerySet,
                                compute_resource: Union[str, ComputeResource],
                                allow_delete_default=False) -> int:
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
        old_prefix = f'laxy+sftp://{compute_resource.id}/'
        oldlocs = FileLocation.objects.filter(file__in=files, url__startswith=old_prefix)
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
