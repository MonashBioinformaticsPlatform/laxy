import fnmatch
import shlex
import traceback
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from typing import Dict, Mapping, Sequence, Union, Iterable, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import logging
import os
from os.path import join, expanduser, relpath, dirname
import random
import time
import json
import base64
from io import BytesIO
from copy import copy
from contextlib import closing
from django.conf import settings
from django.db.models import QuerySet
from django.db import IntegrityError

from paramiko.config import SSHConfig
from paramiko.ssh_exception import SSHException

from celery.result import AsyncResult
from django.contrib.contenttypes.models import ContentType
from django.template import TemplateDoesNotExist
from django.template.loader import get_template, render_to_string, select_template
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (
    Ignore,
    InvalidTaskError,
    TimeLimitExceeded,
    SoftTimeLimitExceeded,
)

from guardian.utils import clean_orphan_obj_perms as guardian_clean_orphan_obj_perms

import requests
import cgi
import backoff

from fabric.api import settings as fabsettings
from fabric.api import env as fabric_env
from fabric.api import put, run, shell_env, local, cd, show, hide

# logging.config.fileConfig('logging_config.ini')
# logger = logging.getLogger(__name__)
from ..models import (
    Job,
    File,
    EventLog,
    ComputeResource,
    FileLocation,
    get_primary_compute_location_for_files,
    job_path_on_compute,
    get_compute_resources_for_files,
)
from ..util import generate_uuid, laxy_sftp_url, get_traceback_message

from .file import add_file_replica_records, move_file_task
from .verify import verify, verify_task, VerifMode

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


def get_app_job_template_paths() -> Mapping[str, str]:
    """
    Iterate over installed apps, find the path to the job skeleton templates
    for any app that defines apps.LAXY_PIPELINE_NAME (in apps.py for each
    app). Returns a dictionary of {pipeline_name: job_templates_absolute_path}.
    """

    from django.apps import apps
    import importlib

    job_template_paths = {}
    for app in apps.get_app_configs():

        app_settings = None
        try:
            # app_settings = importlib.import_module(f"{app.module.__name__}.settings")
            app_settings = importlib.import_module(f"{app.module.__name__}.apps")
        except ModuleNotFoundError:
            pass

        pipeline_name = getattr(app_settings, "LAXY_PIPELINE_NAME", None)
        tmpl_path = getattr(app_settings, "LAXY_JOB_TEMPLATES", None)
        if (pipeline_name is not None) and (tmpl_path is not None):
            if not Path(tmpl_path).is_absolute():
                tmpl_path_abs = str(Path(app.path, tmpl_path))
            else:
                tmpl_path_abs = str(Path(tmpl_path))
            job_template_paths[pipeline_name] = tmpl_path_abs

    return job_template_paths


def get_job_template_files(pipeline_name, pipeline_version):
    """[summary]
    Recursively searches paths containing job skeleton templates
    for the given pipeline and version, returning a dictionary
    of files found ({relpath: abspath}). There may be default
    and version specific copies of the template. Order of precedence is:
      - A 'common' fallback template set for all jobs.
      - A 'default' template set for that pipeline.
      - A 'version' specific template set, which takes precedence over
        any 'common' or 'default' templates with the same relative path.

    Job skeleton templates are searched for in the path specified by
    settings.JOB_TEMPLATE_PATHS, as well as any installed Django apps
    that set LAXY_JOB_TEMPLATES in their own apps.py.

    Args:
        pipeline_name (str): the Pipeline.name

    Raises:
        ImproperlyConfigured: when job_scripts root path can't be found.

    Returns:
        dict: a mapping of relative paths to absolute paths for each file
              discovered.
    """
    from glob import glob
    from toolz.dicttoolz import merge as merge_dicts

    def rglobdict(pathspec: str, relative_to: str = "") -> Mapping[str, str]:
        """
        >>> rglobdict('/tmp/bla/foo/*.txt', relative_to='/tmp/bla')
        {'foo/bar.txt': '/tmp/bla/foo/bar.txt'}
        """
        return {
            os.path.relpath(p, relative_to): p
            for p in set(glob(pathspec, recursive=True))
            if not Path(p).is_dir()
        }

    # baseline templates to always be included for every job,
    # unless overridden by a pipeline specific default or version-level template
    common_template_path = str(
        Path(settings.BASE_DIR, "laxy_backend/templates/common/job")
    )

    # job_template_dirs = ["job_scripts"]  # search paths for job templates from settings
    job_template_dirs = getattr(
        settings,
        "JOB_TEMPLATE_PATHS",
        [str(Path(settings.BASE_DIR, "job_scripts"))],
    )

    job_template_base = None

    # First see if a matching installed pipeline app exists
    pipeline_app_template_paths = get_app_job_template_paths()
    job_template_base = pipeline_app_template_paths.get(pipeline_name, None)
    if job_template_base is not None:
        job_template_base = str(Path(job_template_base, "job_scripts", pipeline_name))

    # Otherwise fallback to templates included with laxy_backend and in
    # configurable path JOB_TEMPLATE_PATHS
    if job_template_base is None:
        for d in job_template_dirs:
            p = Path(d, "job_scripts", pipeline_name)
            if p.is_dir():
                job_template_base = str(p)

    if job_template_base is None:
        raise ImproperlyConfigured(
            f"Cannot find job templates for {pipeline_name}. "
            f"Searched {', '.join([str(j) for j in job_template_dirs])}."
            f" Please add job template files for this pipeline to one of these paths, "
            f"or add your job templates path to settings"
        )

    job_version_files = rglobdict(
        f"{job_template_base}/{pipeline_version}/**/*",
        relative_to=f"{job_template_base}/{pipeline_version}",
    )
    job_default_files = rglobdict(
        f"{job_template_base}/default/**/*",
        relative_to=f"{job_template_base}/default",
    )
    common_files = rglobdict(
        f"{common_template_path}/**/*", relative_to=common_template_path
    )

    out_paths = merge_dicts(
        common_files, job_default_files, job_version_files
    )  # later takes precedence

    return out_paths


@shared_task(bind=True, track_started=True)
def start_job(self, task_data=None, **kwargs):
    from ..models import Job

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get("job_id")
    job = Job.objects.get(id=job_id)
    result = task_data.get("result")
    host = job.compute_resource.host
    gateway = job.compute_resource.gateway_server

    environment = task_data.get("environment", {})
    job_auth_header = task_data.get("job_auth_header", "")
    # environment.update(JOB_ID=job_id)
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get("username", None)

    pipeline_name = job.params.get("pipeline")
    pipeline_version = job.params.get("params", {}).get("pipeline_version", "default")
    job_script_template_vars = dict(environment)

    def template_filelike(fpath):
        return BytesIO(
            render_to_string(fpath, context=job_script_template_vars).encode("utf-8")
        )

    config_json = BytesIO(json.dumps(job.params).encode("utf-8"))
    job_script_template_vars["JOB_AUTH_HEADER"] = job_auth_header
    curl_headers = BytesIO(b"%s\n" % job_auth_header.encode("utf-8"))

    job_script_path = "input/scripts/run_job.sh"

    # We prepare a dictionary like {remote_relative_path: local_absolute_path} of
    # job skeleton template files. eg:
    # {
    #  'kill_job.sh': ' /app/laxy_backend/templates/common/job/kill_job.sh',
    #  'input/scripts/laxy.lib.sh': '/app/laxy_backend/templates/common/job/input/scripts/laxy.lib.sh',
    #  'input/scripts/add_to_manifest.py': '/app/seqkit-stats-laxy-pipeline-app/templates/job_scripts/seqkit_stats/default/input/scripts/add_to_manifest.py',
    #  'input/scripts/run_job.sh': '/app/seqkit-stats-laxy-pipeline-app/templates/job_scripts/seqkit_stats/default/input/scripts/run_job.sh',
    #  'input/config/conda_environment.yml': '/app/seqkit-stats-laxy-pipeline-app/templates/job_scripts/seqkit_stats/default/input/config/conda_environment.yml'
    # }
    job_template_files = get_job_template_files(pipeline_name, pipeline_version)

    extension_chmod_mappings = {".py": 0o700, ".sh": 0o700}

    def infer_chmod(filename, default=0o600, mappings=extension_chmod_mappings):
        for ext, chmod in mappings.items():
            if filename.endswith(ext):
                return chmod
        return default

    remote_id = None
    message = "Failure, without exception."
    try:
        with fabsettings(
            gateway=gateway,
            host_string=host,
            user=remote_username,
            key=private_key,
            # key_filename=expanduser("~/.ssh/id_rsa"),
        ):
            working_dir = job.abs_path_on_compute
            remote_subdirs = [
                join(working_dir, os.path.dirname(remote_relpath))
                for remote_relpath in job_template_files.keys()
            ]
            # Ensure input and output exist
            remote_subdirs.append(join(working_dir, "input/config"))
            remote_subdirs.append(join(working_dir, "output"))

            for d in set(remote_subdirs):
                result = run(f"mkdir -p {d} && chmod 700 {d}")

            # TODO/IDEA: Treat only .j2 files as templates where we apply a context dict,
            #       remove the .j2 extension when copying
            for remote_relpath, local_fpath in job_template_files.items():
                fmode = infer_chmod(remote_relpath)
                if local_fpath:
                    flike = template_filelike(local_fpath)
                    put(flike, join(working_dir, remote_relpath), mode=fmode)

            result = put(
                curl_headers, join(working_dir, ".private_request_headers"), mode=0o600
            )
            result = put(
                config_json,
                join(working_dir, "input/config/pipeline_config.json"),
                mode=0o600,
            )
            with cd(working_dir):
                with shell_env(**environment):
                    cpus = 1
                    mem = "4G"
                    time = "7-00:00:00"
                    logger.info(f"queue_type = {job.compute_resource.queue_type}")
                    if job.compute_resource.queue_type == "slurm":
                        result = run(
                            f"sbatch --parsable "
                            f'--job-name="laxy:{job_id}" '
                            f"--output output/run_job.out "
                            f"--cpus-per-task={cpus} "
                            f"--mem={mem} "
                            f"--time={time} "
                            f"{job_script_path} "
                            f" >>slurm.jids"
                        )
                        remote_id = run(str("head -1 slurm.jids"))
                    else:
                        # The job script is always run locally on the compute
                        # node (not sbatched), but will itself send jobs
                        # to the queue.
                        result = run(
                            f"nohup bash -l -c '"
                            f"{job_script_path} & "
                            f"echo $! >>job.pids"
                            f"' >output/run_job.out"
                        )
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


def get_job_expiry_for_status(status: str) -> datetime:
    _hours = 60 * 60
    if status == Job.STATUS_CANCELLED:
        ttl = getattr(settings, "JOB_EXPIRY_TTL_CANCELLED", 0)
    elif status == Job.STATUS_FAILED:
        ttl = getattr(settings, "JOB_EXPIRY_TTL_FAILED", 72 * _hours)
    else:
        ttl = getattr(settings, "JOB_EXPIRY_TTL_DEFAULT", 30 * 24 * _hours)

    expiry_time = timezone.now() + timedelta(seconds=ttl)
    return expiry_time


@shared_task(bind=True, track_started=True)
def set_job_status(self, task_data=None, **kwargs):
    from ..models import Job, File

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    job_id = task_data.get("job_id")
    status = task_data.get("status")
    with transaction.atomic():
        job = Job.objects.get(id=job_id)
        job.status = status
        job.expiry_time = get_job_expiry_for_status(job.status)
        job.save()

    if (
        job.done
        and job.compute_resource
        and job.compute_resource.disposable
        and not job.compute_resource.running_jobs()
    ):
        job.compute_resource.dispose()

    return task_data


@shared_task(
    name="index_remote_files",
    queue="low-priority",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    track_started=True,
    default_retry_delay=60,
    max_retries=3,
)
def index_remote_files(self, task_data=None, **kwargs) -> dict:
    def _remote_list_files(path=".") -> Sequence[Tuple[str, int]]:
        """
        Recursively list files relative to the specified path,
        returning a list of tuples [(relpath, size)].

        Intended to be called within a Fabric context.

        :param path: A path (absolute or relative to cwd)
        :type path: str
        :return: A list of tuples, (relative file path, byte size).
        :rtype: Sequence[Tuple[str, int]]
        """
        # path = shlex.quote(path)
        # lslines = run(f"find -L '{path}' -mindepth 1 -type f -printf '%P\n'")
        # Get the relative file path and the size
        # -L ensures symlinks are followed and output as filenames too
        # try:
        cmd = f"find -L '{path}'" + " -mindepth 1 -type f -printf '%P\t%s\n'"

        # we use 'hide' to prevent stdout going to log, too noisy
        with hide("output", "warnings"), fabsettings(warn_only=True):
            lslines = run(cmd)

        if not lslines.succeeded:
            logger.error(lslines.stderr)
            raise SystemExit(f"Command {cmd} -- failed to list remote files: {lslines}")

        filepath_size = [l.split("\t") for l in lslines.splitlines() if l.strip()]
        filepath_size = [(pair[0], int(pair[1])) for pair in filepath_size]
        return filepath_size

    # def _stat_filesize(filepath):
    #     s = run(f"stat -L -c %s '{filepath}'")
    #     if s.succeeded:
    #         return int(s.splitlines()[0])
    #     return None

    def _create_update_file_objects(
        filelisting: List[Tuple],
        fileset=None,
        prefix_path="",
        location_base="",
        set_as_default=True,
    ) -> Sequence[File]:
        """
        Returns a list of (unsaved) File objects given a list of relative paths
        and file sizes. If a FileSet is provided and contains file of the same
        path+name then add/update the File's location, otherwise create a
        new File object.

        :param fileset:
        :type fileset:
        :param prefix_path:
        :type prefix_path:
        :param filelisting: A list of tuples, (relative file path, byte size).
        :type filelisting: List[str]
        :param location_base: Prefix of location URL (eg sftp://127.0.0.1/XxX/)
        :type location_base: str
        :param set_as_default: Set the new location as the default for any existing File
        :type set_as_default: bool
        :return: A list of File objects
        :rtype: Sequence[File]
        """

        file_objs = []
        for filepath, filesize in filelisting:
            location = f"{location_base}/{filepath}"
            fname = Path(filepath).name
            fpath = Path(prefix_path, filepath).parent

            f = None
            if fileset:
                f = fileset.get_file_by_path(Path(fpath, fname))

            if not f:
                f = File(location=location, owner=job.owner, name=fname, path=fpath)
            else:
                f.add_location(location, set_as_default=set_as_default)

            if not f.owner:
                f.owner = job.owner

            f.size = filesize

            file_objs.append(f)

        return file_objs

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    if not task_data.get("result", None):  # replace falsy or absent with an empty dict
        task_data["result"] = {}

    job_id = task_data.get("job_id")
    job = Job.objects.get(id=job_id)
    compute_resource_id = task_data.get("compute_resource_id", None)
    clobber = task_data.get("clobber", False)
    remove_missing = task_data.get("remove_missing", True)
    set_as_default = task_data.get("set_as_default", True)
    environment = task_data.get("environment", {})

    # TODO: We could in fact loop over all compute resources where files are
    #       and ingest from each of them (adding duplicates as extra FileLocations)
    #       This would mean jobs split over two hosts (eg due to a failed
    #       move_job_files_task) would still index correctly.
    #
    # stored_at = get_compute_resources_for_files(job.get_files())

    compute_resource = None
    if compute_resource_id:
        compute_resource = ComputeResource.objects.get(id=compute_resource_id)
    else:
        compute_resource = get_primary_compute_location_for_files(job.get_files())
        if compute_resource is None:
            compute_resource = job.compute_resource

    if compute_resource is not None:
        compute_resource_id = compute_resource.id
        host = compute_resource.host
        gateway = compute_resource.gateway_server
    else:
        logger.info(f"Not indexing files for {job_id}, no compute_resource.")
        return task_data

    job.log_event("JOB_INFO", "Indexing all files (backend task)")

    _init_fabric_env()
    private_key = compute_resource.private_key
    remote_username = compute_resource.extra.get("username", None)

    message = "No message."

    try:
        task_data["result"]["n_files_indexed"] = 0

        for fileset_relpath, fileset in [
            ("input", job.input_files),
            ("output", job.output_files),
        ]:

            job_abs_path = job_path_on_compute(job, compute_resource)
            fileset_abspath = str(Path(job_abs_path, fileset_relpath))

            with fabsettings(
                gateway=gateway, host_string=host, user=remote_username, key=private_key
            ):
                with cd(fileset_abspath):
                    filelisting = _remote_list_files(".")

            file_objs = _create_update_file_objects(
                filelisting,
                fileset=fileset,
                prefix_path=fileset_relpath,
                location_base=f"laxy+sftp://{compute_resource.id}/{job.id}/{fileset_relpath}",
                set_as_default=set_as_default,
            )

            # TOOD: Profile this - is it slow ?
            with transaction.atomic():
                fileset.path = fileset_relpath
                fileset.owner = job.owner

                if clobber:
                    fileset.remove(list(fileset.get_files()), delete=True)

                if remove_missing:
                    new_file_pathlist = set([f.full_path for f in file_objs])
                    for old_fobj in fileset.get_files():
                        # We ignore non-laxy+sftp files so we don't unintentionlly
                        # remove files that reside in non-SFTP storage backends, eg
                        # object store etc
                        # (eg, a pipeline might stream files directly from object store,
                        #  or registers output files output into object store)
                        if (
                            old_fobj.location
                            and urlparse(old_fobj.location).scheme.lower()
                            != "laxy+sftp"
                        ):
                            continue
                        if old_fobj.full_path not in new_file_pathlist:
                            fileset.remove(old_fobj, delete=True)

                fileset.add(file_objs)

                fileset.save()

                task_data["result"]["n_files_indexed"] += len(file_objs)

        succeeded = True
    except BaseException as ex:
        succeeded = False
        if hasattr(ex, "message"):
            message = ex.message

        self.retry(exc=ex, countdown=60)

    return task_data


@shared_task(bind=True)
def _finalize_job_task_err_handler(self, task_id, job_id=None):
    logger.info(
        f"_finalize_job_task_err_handler: failed task: {task_id}, job_id: {job_id}"
    )
    task_result = AsyncResult(task_id)
    job = Job.objects.get(id=job_id)
    if not job.done:
        job.status = Job.STATUS_FAILED
        job.save()

        if job.compute_resource and job.compute_resource.disposable:
            job.compute_resource.dispose()

        eventlog = job.log_event(
            "JOB_FINALIZE_ERROR",
            "",
            extra={
                "task_id": task_id,
                "exception": str(task_result.result),
                "traceback": task_result.traceback,
            },
        )
        message = (
            f"Failed to index files or finalize job status (Celery Task ID: {task_id})"
        )
        eventlog.message = message
        eventlog.save()


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

    job_id = task_data.get("job_id")
    job = Job.objects.get(id=job_id)
    host = job.compute_resource.host
    gateway = job.compute_resource.gateway_server
    _init_fabric_env()
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get("username", None)

    message = "No message."
    try:
        with fabsettings(
            gateway=gateway, host_string=host, user=remote_username, key=private_key
        ):
            with shell_env():
                result = run(
                    f"ps - u {remote_username} -o pid | "
                    f"tr -d ' ' | "
                    f"grep '^{job.remote_id}$'"
                )
                job_is_not_running = not result.succeeded

    except BaseException as e:
        if hasattr(e, "message"):
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

    environment = task_data.get("environment", {})
    job_id = task_data.get("job_id")
    job = Job.objects.get(id=job_id)
    if not job.compute_resource:
        logger.warning(
            f"Attempting to kill job without a ComputeResource ({job_id}) - ignoring"
        )
        return task_data

    host = job.compute_resource.host
    gateway = job.compute_resource.gateway_server
    queue_type = job.compute_resource.queue_type
    private_key = job.compute_resource.private_key
    remote_username = job.compute_resource.extra.get("username", None)

    working_dir = job.abs_path_on_compute
    kill_script_path = join(working_dir, "kill_job.sh")

    message = "No message."
    try:
        with fabsettings(
            gateway=gateway, host_string=host, user=remote_username, key=private_key
        ):
            with cd(working_dir):
                with shell_env(**environment):
                    # if queue_type == 'slurm':
                    #     result = run(f"scancel {job.remote_id}")
                    # else:
                    #     result = run(f"kill {job.remote_id}")

                    result = run(f"{kill_script_path} kill")
                    job_killed = result.succeeded

    except BaseException as e:
        if hasattr(e, "message"):
            message = e.message

        self.update_state(state=states.FAILURE, meta=message)
        raise e

    task_data.update(
        result={
            "kill_remote_job": {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.return_code,
            }
        }
    )

    return task_data


@shared_task(
    queue="low-priority",
    bind=True,
    track_started=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def estimate_job_tarball_size(
    self, task_data=None, optional=False, use_heuristic=False, **kwargs
):
    task_result = dict()
    try:
        if task_data is None:
            raise InvalidTaskError("task_data is None")

        from ..models import Job

        _init_fabric_env()

        environment = task_data.get("environment", {})

        job_id = task_data.get("job_id")
        job = Job.objects.get(id=job_id)
        # stored_at = get_primary_compute_location_for_files(job.get_files())
        compute_locs = [
            c for c in get_compute_resources_for_files(job.get_files()) if c is not None
        ]
        if not compute_locs:
            raise Exception("Job files have no ComputeResource location(s) ?")

        stored_at = compute_locs.pop()
        host = stored_at.host
        gateway = stored_at.gateway_server
        queue_type = stored_at.queue_type
        private_key = stored_at.private_key
        remote_username = stored_at.extra.get("username", None)

        job_path = job_path_on_compute(job, stored_at)

        # If running tar -chzf is too slow / too much extra I/O load,
        # we can get a rough idea using du instead and a scaling factor
        # to account for compression.
        # We run as 'nice' since this is considered low priority.
        quick_mode = use_heuristic or task_data.get("tarball_size_use_heuristic", False)
        compression_scaling = 1
        cmd = (
            f'nice tar -chzf - --restrict --directory "{job_path}" . | nice wc --bytes'
        )
        if quick_mode:
            # This compression ratio seems reasonable for RNAsik runs. Will likely be different
            # for different data types.
            compression_scaling = 0.66
            cmd = f'nice du -bc --max-depth=0 "{job_path}" | tail -n 1 | cut -f 1'

        def tar_threw_error(stdout_txt):
            tar_error_messages = [
                "File changed as we read it",
                "File removed before we read it",
            ]
            return any(
                [
                    err.lower() in stdout_txt.strip().lower()
                    for err in tar_error_messages
                ]
            )

        if not stored_at.available:
            with transaction.atomic():
                job = Job.objects.get(id=job_id)
                job.params["tarball_size"] = 0
                job.save(update_fields=["params", "modified_time"])
                task_result["tarball_size"] = 0
                task_result["stdout"] = None
                task_result["stderr"] = None
                task_data.update(result=task_result)

                return task_data

        with fabsettings(
            gateway=gateway, host_string=host, user=remote_username, key=private_key
        ):
            with cd(job_path):
                with shell_env(**environment):
                    result = run(cmd)
                    tries = 0
                    while (
                        result.succeeded
                        and tar_threw_error(result.stdout)
                        and tries <= 3
                    ):
                        result = run(cmd)
                        tries += 1

                    if result.succeeded:
                        if tar_threw_error(result.stdout):
                            raise Exception(
                                f"Files continue to change while calculating tarball size for "
                                f"Job: {job.id}"
                            )

                        tarball_size = int(result.stdout.strip()) * compression_scaling
                        with transaction.atomic():
                            job = Job.objects.get(id=job_id)
                            job.params["tarball_size"] = tarball_size
                            job.save(update_fields=["params", "modified_time"])

                        task_result["tarball_size"] = tarball_size
                    else:
                        task_result["stdout"] = result.stdout.strip()
                        task_result["stderr"] = result.stderr.strip()

    except BaseException as ex:
        message = get_traceback_message(ex)
        self.update_state(state=states.FAILURE, meta=message)
        if not optional:
            raise ex

    task_data.update(result=task_result)

    return task_data


# TODO: This function is very pipeline specific (RNAsik) - we need to refactor
#       to take the pipeline into account (eg based on name in Job.params.params.pipeline)
#       The various variables/rules for this function could also be declarative and
#       stored in the Pipeline model, or a new PipelineConfig object. The defaults
#       could come from the Django app that defines the pipeline.
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
    whitelisted_extensions = [".txt", ".html", ".log"]
    whitelisted_paths = [
        "**/sikRun/multiqc_data/**",
        "**/sikRun/fastqcReport/**",
        "**/sikRun/countFiles/**",
        "**/sikRun/logs/**",
    ]
    whitelisted_type_tags = ["report", "counts", "degust"]
    always_delete_extensions = [".tmp", ".bam", ".bai", ".bw", ".bedGraph"]
    always_delete_paths = [
        "**/sikRun/refFiles/**",
        "input/*.fastq.gz",
        "input/*.fastq",
        "input/*.fq.gz", 
        "input/**/*.fastq.gz",
        "input/**/*.fastq",
        "input/**/*.fq.gz",
        "input/reads/*",
        "input/reads/**/*",
        #"input/reference/*",
    ]

    if extension in always_delete_extensions:
        return True

    has_always_delete_path = any(
        [fnmatch.filter([ff.full_path], pattern) for pattern in always_delete_paths]
    )
    if has_always_delete_path:
        return True

    if ff.size is not None:
        is_large_file = (ff.size / MB) > max_size
    else:
        logger.warning(
            f"Cannot determine size of file {ff.id} (file_should_be_deleted). "
            f"Erring on the side of caution and regarding this file as 'small', but be warned - "
            f"if it's large it may hang around even though we'd rather it expired."
        )
        is_large_file = False

    has_whitelisted_path = any(
        [fnmatch.filter([ff.full_path], pattern) for pattern in whitelisted_paths]
    )
    
    has_whitelisted_tag = False
    if ff.type_tags is not None:
        has_whitelisted_tag = any([tag in whitelisted_type_tags for tag in ff.type_tags])

    return (
        (not ff.deleted)
        and is_large_file
        and (extension not in whitelisted_extensions)
        and (not has_whitelisted_tag)
        and (not has_whitelisted_path)
    )


@shared_task(
    queue="low-priority",
    bind=True,
    track_started=True,
)
def expire_old_job(self, task_data=None, **kwargs):
    from ..models import Job, File

    _init_fabric_env()

    seconds_in_day = 60 * 60 * 24
    ttl = task_data.get("ttl", 30 * seconds_in_day)
    MB = 1024 * 1024

    environment = task_data.get("environment", {})
    job_id = task_data.get("job_id")
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
    old_files = (
        job.get_files()
        .filter(created_time__lt=timezone.now() - timedelta(seconds=ttl))
        .all()
    )
    message = "No message."
    try:
        count = 0
        deferred_exception = None
        for f in old_files:
            try:
                if file_should_be_deleted(f):
                    _size_str = ""
                    if f.size is not None:
                        _size_str = f"({f.size / MB:.1f}MB)"
                    logger.info(f"Deleting {job.id} {f.full_path} {_size_str}")
                    try:
                        # NOTE: There are temporary states where a file will fail to delete (network outage),
                        #       and permanent states where deletion will fail (ComputeResource no longer exists).
                        #       A job isn't marked as expired until we've successfully deleted the files that should
                        #       be deleted - but we need a way to decide that after many attempts over a reasonable
                        #       time, a file can be marked as deleted because we can't access the storage backend.
                        f.delete_file()
                        count += 1
                    except NotImplementedError:
                        logger.warning(
                            f"Unable to delete {job.id} {f.full_path} "
                            f"(NotImplementedError for this file location)"
                        )
            except FileNotFoundError as ex:
                if f.locations.count() == 0:
                    logger.info(
                        f"File {f.id} doesn't exist on backend storage and no locations remain - marking as expired"
                    )
                    f.deleted_time = timezone.now()
                    f.save()
                else:
                    logger.info(
                        f"File {f.id} is missing at one location, but still exists a some locations. Not marking as expired."
                    )
                    if deferred_exception is None:
                        deferred_exception = ex

            except BaseException as ex:
                # If any file can't be deleted for unknown reasons, ensure we don't mark the job as expired by
                # raising an exception before that happens. This way rhe scheduled task will try again later.
                logger.error(
                    f"Unable to delete File {f.id} in Job {job.id}:",
                    get_traceback_message(ex),
                )
                if deferred_exception is None:
                    deferred_exception = ex

        if deferred_exception is not None:
            raise deferred_exception

        job.expired = True
        job.save()
        result = {"deleted_count": count}

        try:
            if count > 0:
                r = estimate_job_tarball_size.apply_async(
                    args=(
                        dict(
                            job_id=job.id,
                        ),
                    )
                )
                if r.failed():
                    raise r.result
        except BaseException as ex:
            logger.error(
                f"Failed to start estimate_job_tarball_size task after expiring Job ({job.id}) [{get_traceback_message(ex)}]"
            )
            pass

        try:
            job.log_event("JOB_INFO", "Job expired, some files may be unavailable.")
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
    expiring_jobs = (
        Job.objects.filter(expired=False, expiry_time__lte=timezone.now())
        .exclude(expiry_time__isnull=True)
        .exclude(status=Job.STATUS_RUNNING)
        .order_by("-expiry_time")
    )
    for job in expiring_jobs:
        logging.info(f"Expiring job: {job.id}")
        expire_old_job.s(task_data=dict(job_id=job.id)).apply_async()


@shared_task(
    bind=True,
    track_started=True,
    acks_late=True,
    reject_on_worker_lost=True,
    default_retry_delay=60 * 60,
    max_retries=5,
    # autoretry_for=(IOError, OSError,),
    retry_backoff=600,  # 10 min, doubling each retry
    retry_backoff_max=60 * 60 * 48,  # 48 hours
)
def move_job_files_to_archive_task(self, task_data=None, *kwargs):
    from ..models import Job, File
    from ..util import split_laxy_sftp_url

    def _move_untracked_files(
        job: Job, src_compute: ComputeResource, dst_compute: ComputeResource
    ):
        """
        Temporary function that moves files not in input/ and output/ directories, that
        may not be tracked by Laxy File objects in the database.
        """
        job_src_path = job_path_on_compute(job, src_compute)
        _, fpaths = src_compute.sftp_storage.listdir(job_src_path)
        fpaths = [str(Path(job_src_path, fn)) for fn in fpaths]

        for src_fp in fpaths:
            bakfile = None
            dst_path = job_path_on_compute(job, dst_compute)
            dst_fp = str(Path(dst_path) / Path(src_fp).name)
            dst_sftp = dst_compute.sftp_storage
            src_sftp = src_compute.sftp_storage
            if src_sftp.exists(src_fp):
                with src_sftp.open(src_fp, "r") as fh:
                    if dst_sftp.exists(dst_fp):
                        bakfile = str(
                            Path(dst_fp).parent / Path("." + Path(dst_fp).name)
                        )
                        dst_sftp.sftp.posix_rename(dst_fp, bakfile)
                    dst_sftp.save(dst_fp, fh)
                    # chmod to match dst with src
                    src_mode: int = src_sftp.sftp.stat(src_fp).st_mode
                    dst_sftp.sftp.chmod(dst_fp, src_mode)

            if bakfile is not None:
                dst_sftp.delete(bakfile)
                bakfile = None

            if dst_sftp.exists(dst_fp) and src_sftp.exists(src_fp):
                src_sftp.delete(src_fp)

        return fpaths

    job_id = task_data.get("job_id")
    job = Job.objects.get(id=job_id)

    results = {}
    immediate_failed = []
    skipped = []
    n_started = 0
    # task_list = []

    for file in job.get_files():
        try:
            if file.location is None:
                logger.error(
                    f"File {file.id} has no location. Skipping copy_to_archive for this file."
                )
                skipped.append(file.id)
                continue

            # Moving from default file location
            # (not always the _original_ compute location, in the case where we've moved once already)
            src_compute, _job, path, filename = split_laxy_sftp_url(
                file.location, to_objects=True
            )

            src_prefix = f"laxy+sftp://{src_compute.id}/"

            if job.compute_resource.archive_host:
                dst_compute_id = job.compute_resource.archive_host.id
            else:
                immediate_failed.append(file.id)
                logger.error(
                    f"Job for file {file.id} has no archive_host set. Skipping copy_to_archive for this file."
                )
                continue

            dst_prefix = f"laxy+sftp://{dst_compute_id}/"
            from_location = str(file.location)
            to_location = str(file.location).replace(src_prefix, dst_prefix, 1)

            # TODO: Consider using a Group call here (parallel) and return failed/succeeded
            #       IDs from the GroupResult, polling on `while group_result.waiting():`
            #       https://docs.celeryproject.org/en/stable/userguide/canvas.html#groups
            #       The advantage is we can retry / reschedule if group_result.failed()
            if from_location != to_location:
                _t_data = dict(
                    file_id=file.id,
                    from_location=from_location,
                    to_location=to_location,
                    clobber=True,
                    # verify_on=VerifMode.CHECKSUM_ELSE_SIZE,
                    verify_on=VerifMode.SIZE,
                )
                celery_result = move_file_task.apply_async(args=(_t_data,))

                # Example of how we might do this with a celery Group instead
                # task_list.append(move_file_task.s(_t_data))

                if celery_result.failed():
                    immediate_failed.append(file.id)
                else:
                    n_started += 1
            else:
                skipped.append(file.id)

        except BaseException as ex:
            pass

    #
    # TODO: Remove this extra step once /manifest.csv etc are tracked as model.Files
    #
    # job.get_files() doesn't include files below input/ and output/ (they aren't tracked as models.Files).
    # We need to either transfer these seperately (:/ yeck) or register them (which may require moving them to
    # to input/ or output/ due to current inflexibility of Job filesets)
    # Files are: job.pids, kill_job.sh, manifest.csv, slurm.jids
    try:
        fpaths = _move_untracked_files(
            job, job.compute_resource, job.compute_resource.archive_host
        )
        results["_move_untracked_files"] = fpaths
    except BaseException as ex:
        results["_move_untracked_files"] = "failed"
        raise ex

    # Example of how we might do this with a celery Group instead
    # task_group = group(task_list)
    # group_result = task_group()
    # while group_result.waiting():
    #     time.sleep(30)
    # successful_task_results = [r.result for r in group_result.join() if r.successful()]
    # failed_task_exceptions = [r.result for r in group_result.join() if r.failed()]

    results["n_started"] = n_started
    results["immediate_failed"] = immediate_failed
    results["skipped"] = skipped
    task_data["result"] = results
    return task_data


@shared_task(
    queue="low-priority",
    bind=True,
    track_started=True,
    acks_late=True,
    reject_on_worker_lost=True,
    default_retry_delay=60,          # 1min
    max_retries=10,
    autoretry_for=(IOError, OSError, SSHException),
    retry_backoff=120,               # 2 min, doubling each retry
    retry_backoff_max=60 * 60 * 72,  # 72 hours
)
def bulk_move_job_rsync(self, task_data=None, optional=False, **kwargs):
    """
    Move all job files from the original compute resource to another
    (usually the archive host) using rsync.

    Updates default file locations and deletes original copy at source
    when completed successfully.

    Note that this task requires that the source trusts the destination
    via ~/.ssh/authorized_keys. rsync is run on the destination, pulling
    from the source over SSH.
    """
    task_result = dict()
    try:
        if task_data is None:
            raise InvalidTaskError("task_data is None")

        from ..models import Job

        _init_fabric_env()

        environment = task_data.get("environment", {})

        job_id = task_data.get("job_id")
        job = Job.objects.get(id=job_id)
        src_compute = task_data.get("src_compute_id", None)
        if src_compute is not None:
            src_compute = ComputeResource.objects.get(id=src_compute)
        else:
            src_compute = job.compute_resource

        dst_compute = task_data.get("dst_compute_id", None)
        if dst_compute is not None:
            dst_compute = ComputeResource.objects.get(id=dst_compute)
        else:
            dst_compute = job.compute_resource.archive_host

        src_job_path = job_path_on_compute(job, src_compute)
        src_userstr = src_compute.extra.get("username", "")
        if src_userstr != "":
            src_userstr = f"{src_userstr}@"

        src_str = f"{src_userstr}{src_compute.host}:/{src_job_path}"

        # TODO: Ignoring host keys (-o Stricthostkeychecking=no) isn't ideal- we should ideally
        #       add the host key to ComputeResource.extra.host_keys and use
        #       -o "UserKnownHostsFile /tmp/.laxy/ssh/known_hosts-{src_compute.id}_{generate_uuid()}"
        #       as a host key file, generated alongside the temporary private key file.
        #       The `ssh-keyscan compute_resource.hostname` can find the host keys - we could also do this
        #       automatically if compute_resource.host_keys isn't present, emulating the behaviour of
        #       ~/.ssh/known_hosts but associated with the ComputeResource record.

        make_dst_new_default = task_data.get("make_default", True)

        host = dst_compute.host
        gateway = dst_compute.gateway_server
        private_key = dst_compute.private_key
        remote_username = dst_compute.extra.get("username", None)
        rsync_succeeded = False
        with fabsettings(
            gateway=gateway, host_string=host, user=remote_username, key=private_key
        ):
            with shell_env(**environment):
                # src_compute must trust dst_compute
                # (eg the key for dst_compute is in ~/.ssh/authorized_keys on src_compute)
                # generate_uuid is random, so the path to the temporary private key should
                # be unguessable
                tmpkeyfn = f"/tmp/.laxy/ssh/id_rsa-{src_compute.id}_{generate_uuid()}"
                cmd = (
                    f"nice rsync -avsL -e "
                    f'"ssh -i {tmpkeyfn} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" '
                    f'"{src_str}" "{dst_compute.jobs_dir}/"; '
                    f"rm -f {tmpkeyfn}"
                )

                _tmpdirpath = Path(tmpkeyfn).parent
                result = run(f"mkdir -p {_tmpdirpath} && chmod 700 {_tmpdirpath}")
                result = put(
                    BytesIO(src_compute.private_key.encode("utf-8")),
                    tmpkeyfn,
                    mode=0o600,
                )

                result = run(cmd)
                task_result["stdout"] = result.stdout.strip()
                task_result["stderr"] = result.stderr.strip()
                task_result["exit_code"] = result.return_code

                rsync_succeeded = result.succeeded

        src_prefix = f"laxy+sftp://{src_compute.id}/"
        dst_prefix = f"laxy+sftp://{dst_compute.id}/"
        if rsync_succeeded:
            for file in job.get_files():

                from_location = str(file.location)
                to_location = str(file.location).replace(src_prefix, dst_prefix, 1)

                # If file location hasn't been set, we assume the to/from
                # locations are the same as the rsync destination. File existance
                # check next will verify that it's there.
                # TODO: Verify md5sum in this case, if set
                if file.location == "" or file.location is None:
                    to_location = f"{dst_prefix}{file.path}/{file.name}"
                    from_location = to_location

                if file.exists(loc=to_location):
                    # Make destination the new default file location
                    add_file_replica_records([file], dst_compute, set_as_default=True)
                    # Get file record from database again to ensure our record is fresh and has both locations
                    _updated_file_record = File.objects.get(id=file.id)
                    # Delete the real file at the old location, remove old location record
                    if (
                        from_location != to_location
                        and _updated_file_record.locations.filter(
                            url=from_location
                        ).exists()
                    ):
                        _updated_file_record.delete_at_location(
                            from_location, allow_delete_default=False
                        )
    except (OSError, IOError, SSHException) as ex:
        self.retry(exc=ex)
    except BaseException as ex:
        message = get_traceback_message(ex)
        self.update_state(state=states.FAILURE, meta=message)
        if not optional:
            raise ex

    task_data.update(result=task_result)

    return task_data


@shared_task(bind=True, track_started=True)
def clean_orphan_obj_perms():
    return guardian_clean_orphan_obj_perms()
