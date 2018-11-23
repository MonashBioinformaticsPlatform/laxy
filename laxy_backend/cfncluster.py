
def generate_cluster_stack_name(job):
    """
    Given a job, generate a name for an associated compute cluster resource.

    Since this becomes an AWS (or OpenStack?) Stack name via CloudFormation
    it can only contain alphanumeric characters (upper and lower) and hyphens
    and cannot be longer than 128 characters.

    :param job: A Job instance (with ComputeResource assigned)
    :type job: Job
    :return: A cluster ID to use as the stack name.
    :rtype: str
    """
    return 'cluster-%s----%s' % (job.compute_resource.id, job.id)


# import os
# import requests
# from django.conf import settings
# from celery import chain
# from celery import shared_task
# from rest_framework import status
# from rest_framework.request import Request
# from rest_framework.response import Response
# from rest_framework.authtoken.models import Token
#
# from .serializers import JobSerializerRequest
# from .views import _get_default_compute_resource
# from . import tasks
# from . import jwt_helpers
# from . import bcbio
#
# from django.contrib.auth import get_user_model
# User = get_user_model()
#
# PUBLIC_IP = requests.get('https://checkip.amazonaws.com').text

# ##
# # Originally a (POST) method on the JobCreate view, preserved here  ...
# ##
# def _post_cfn_cluster_create_flow(request: Request, version=None):
#     serializer = JobSerializerRequest(data=request.data,
#                                       context={'request': request})
#     if serializer.is_valid():
#
#         job = serializer.save()  # owner=request.user)
#
#         if not job.compute_resource:
#             job.compute_resource = _get_default_compute_resource()
#             job.save()
#
#         job_id = job.id
#
#         # HACK: Testing
#         # job_id = '1ddIMaKJ9PY8Kug0dW1ubO'
#
#         # callback_url = request.build_absolute_uri(
#         #     reverse('laxy_backend:job', args=[job_id]))
#
#         # the request header called "Authorization"
#         auth_token = request.META.get(
#             'HTTP_AUTHORIZATION',
#             jwt_helpers.get_jwt_user_header_dict(request.user.username))
#
#         # TODO: The location of this template should be defined in settings
#         #       It's a jinja2 template that lives on the Django host.
#         #       We should also pass in a dictionary of values here to fill
#         #       out the template (derived from settings and/or based on
#         #       job params) and make a tmp copy, which is the actual path
#         #       we pass in as config_template.
#         #       Inside cfncluster.start_cluster, we should copy this config
#         #       file to the cluster management host and use it.
#         default_cluster_config = os.path.expanduser('~/.cfncluster/config')
#
#         port = request.META.get('SERVER_PORT', 8001)
#         # domain = get_current_site(request).domain
#         # public_ip = requests.get('https://api.ipify.org').text
#         callback_url = (u'{scheme}://{domain}:{port}/api/v1/job/{job_id}/'.format(
#             scheme=request.scheme,
#             domain=PUBLIC_IP,
#             port=port,
#             job_id=job_id))
#
#         # better alternative to test
#         # callback_url = reverse('job', args=[job_id])
#
#         # Create a JWT object-level access token
#         # Authorization: Bearer bl4F00l33th4x0r
#         # callback_auth_header = '%s: %s' % make_jwt_header_dict(
#         #     create_object_access_jwt(job)).items().pop()
#
#         job_bot, _ = User.objects.get_or_create(username='job_bot')
#         token, _ = Token.objects.get_or_create(user=job_bot)
#         callback_auth_header = 'Authorization: Token %s' % token.key
#
#         task_data = dict(job_id=job_id,
#                          compute_resource_id=job.compute_resource.id,
#                          config_template=default_cluster_config,
#                          gateway=settings.CLUSTER_MANAGEMENT_HOST,
#                          environment={'SCHEDULER': u'slurm_simple',
#                                       'JOB_COMPLETE_CALLBACK_URL':
#                                           callback_url,
#                                       'JOB_COMPLETE_AUTH_HEADER':
#                                           callback_auth_header,
#                                       })
#
#         task_data['environment'].update(bcbio.get_bcbio_run_job_env(job))
#         task_data.update(bcbio.get_bcbio_task_data(job))
#
#         s3_location = 's3://{bucket}/{job_id}/{s3_path}'.format(
#             bucket=settings.S3_BUCKET,
#             job_id=job_id,
#             s3_path='input',
#         )
#
#         task_data.update(s3_location=s3_location)
#
#         # TESTING: Just the upload tasks
#         # tasks.create_job_object_store.apply_async(args=(task_data,))
#         # tasks.upload_input_data_to_object_store.apply_async(args=(task_data,))
#
#         # TESTING: Just starting the cluster
#         # tasks.start_cluster.apply_async(args=(task_data,))
#
#         # TESTING: Start cluster, run job, (pre-existing data), stop cluster
#         # tasks.run_job_chain(task_data)
#
#         # TESTING:
#         # task_data.update(master_ip='52.62.13.233')
#
#         # TESTING: make cluster non-disposable
#         # job.compute_resource.disposable = False
#         # job.compute_resource.save()
#
#         result = chain(tasks.create_job_object_store.s(task_data),
#                        tasks.upload_input_data_to_object_store.s(),
#                        tasks.start_cluster.s(),
#                        tasks.start_job.s(),
#                        # webhook called by job when it completes
#                        # or periodic task should stop cluster
#                        # when required
#                        # tasks.stop_cluster.s()
#                        ).apply_async()
#         # TODO: Make this error handler work.
#         # .apply_async(link_error=self._task_err_handler.s())
#
#         # Update the representation of the compute_resource to the uuid,
#         # otherwise it is serialized to 'ComputeResource object'
#         serializer.validated_data.update(
#             compute_resource=job.compute_resource.id)
#         # apparently validated_data doesn't include this (if it's flagged
#         # read-only ?), so we add it back
#         serializer.validated_data.update(id=job_id)
#
#         return Response(serializer.validated_data,
#                         status=status.HTTP_201_CREATED)
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
