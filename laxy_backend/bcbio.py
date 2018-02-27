import re
from django.conf import settings

from .util import sh_bool


def munge_sample_descriptions(job):
    """
    Hack: Add a suffix to the description field if it would confuse
    the bcbio automatic R1/R2 paired end detection when the files are
    renamed post-lane merging
    :param job: A Job object
    :type job: Job
    :return:
    :rtype:
    """
    pair_end_re = re.compile(r'_([RI]*)\d$')
    for sample in job.input_files.all():
        if re.match(pair_end_re, sample.description):
            sample.description = '%s_' % sample.description
            sample.save()


def get_bcbio_run_job_env(job):
    """
    Prepare a dictionary of environment variables to be passed to the
    run_job.sh script. These are the bcbio-nextgen specific env vars.

    :param job: The Job.
    :type job: models.Job
    :return: A dictionary of environment variables.
    :rtype: dict
    """
    sample_shortnames = []
    for sample in job.input_files.all():
        sample_shortnames.append(sample.description)

    # We merge files (eg samples split across lanes with
    # bcbio_prepare_samples.py) if there are sample/replicate names
    # duplicated in the list, indicating one file
    # TODO: THIS LOGIC IS STILL WRONG - R1 and R2 of a sample will have
    #       the same description (shortname) but shouldn't be merged.
    merge_files = len(set(sample_shortnames)) != len(sample_shortnames)

    if merge_files:
        munge_sample_descriptions(job)

    return {
        'UPDATE_TOOLS': sh_bool(True),
        'UPDATE_DATA': sh_bool(False),
        'MERGE_FILES': sh_bool(merge_files),
        'DOCKER_IMAGE': settings.BCBIO_DOCKER_IMAGE,
    }


def get_bcbio_task_data(job):
    """
    Prepare a dictionary of variables to be passed to the Celery tasks that
    will start this job. These are the bcbio-nextgen specific variables.

    :param job: The Job.
    :type job: models.Job
    :return: A dictionary of variables to be passed to the Celery task(s).
    :rtype: dict
    """
    samples = []
    for sample in job.input_files.all():
        samples.append(sample.to_dict())

    return dict(samples=samples)
