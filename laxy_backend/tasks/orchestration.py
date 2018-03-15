from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (Ignore,
                               InvalidTaskError,
                               TimeLimitExceeded,
                               SoftTimeLimitExceeded)

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, track_started=True)
def dispose_compute_resource(self, task_data, **kwargs):
    from ..models import Job, ComputeResource

    if task_data is None:
        raise InvalidTaskError("task_data is None")

    compute_resource_id = task_data.get('compute_resource_id', None)
    # result = task_data.get('result')

    if not compute_resource_id:
        job_id = task_data.get('job_id')
        job = Job.objects.get(id=job_id)
        compute_resource_id = job.compute_resource.id

    compute = ComputeResource.objects.get(id=compute_resource_id)

    self.status = ComputeResource.STATUS_TERMINATING
    self.save()

    # TODO: Terminate the compute resource
    #       (different depending on cloud provider, resource type)

    raise NotImplementedError()

    ################################################################
    self.status = ComputeResource.STATUS_DECOMMISSIONED
    self.save()

    return task_data
