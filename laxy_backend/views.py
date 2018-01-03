from django.shortcuts import render

import logging
import os
import re
import requests
import jwt
import uuid
from datetime import datetime, timedelta
from collections import OrderedDict

from django.conf import settings
from django.shortcuts import render
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.contrib.auth import views as auth_views
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import Http404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from rest_framework import generics
from rest_framework import status

from rest_framework.response import Response
# from django.http import HttpResponse, JsonResponse

from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.authtoken.models import Token
from rest_framework.authentication import (TokenAuthentication,
                                           SessionAuthentication,
                                           BasicAuthentication)
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated,
                                        IsAdminUser,
                                        DjangoObjectPermissions)
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from drf_openapi.utils import view_config

from celery import shared_task
from celery import chain, group

import reversion

from braces.views import LoginRequiredMixin, CsrfExemptMixin

from .jwt_helpers import get_jwt_user_header_dict
from .models import Job, ComputeResource
from .serializers import JobSerializer, ComputeResourceSerializer

from . import tasks

from .view_mixins import JSONView, GetMixin, PatchMixin, DeleteMixin, PostMixin

logger = logging.getLogger(__name__)

PUBLIC_IP = requests.get('http://api.ipify.org').text


def sh_bool(boolean):
    """
    Formats a boolean to be passed to a bash script environment (eg run_job.sh)
    :param boolean:
    :type boolean:
    :return: 'yes' or 'no'
    :rtype: str
    """
    if boolean:
        return 'yes'
    else:
        return 'no'


class ComputeResourceView(GetMixin,
                          DeleteMixin,
                          JSONView):
    class Meta:
        model = ComputeResource
        serializer = ComputeResourceSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer
    permission_classes = (IsAdminUser,)

    def get(self, request, uuid):
        """
        Returns info about a ComputeResource, specified by UUID.

        :param request: The request object.
        :type request:
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype:
        ---

        serializer: ComputeResourceSerializer
        """
        return super(ComputeResourceView, self).get(request, uuid)

    def patch(self, request, uuid):
        """

        PATCH: https://tools.ietf.org/html/rfc5789

        :param request:
        :type request:
        :param uuid:
        :type uuid:
        :return:
        :rtype:
        """
        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.Meta.serializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            req_status = serializer.validated_data.get('status', None)
            if (obj.status == ComputeResource.STATUS_STARTING or
                obj.status == ComputeResource.STATUS_ONLINE) and \
                (req_status == ComputeResource.STATUS_DECOMMISSIONED or
                 req_status == ComputeResource.STATUS_TERMINATING):

                # remove the status field supplied in the request.
                # this task will update the status in the database itself
                serializer.validated_data.pop('status')
                tasks.stop_cluster.apply_async(
                    args=({'compute_resource_id': obj.id},))

            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
            # return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class ComputeResourceCreate(PostMixin,
                            JSONView):
    class Meta:
        model = ComputeResource
        serializer = ComputeResourceSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer
    permission_classes = (IsAdminUser,)

    @method_decorator(csrf_exempt)
    def post(self, request):
        """
        Create a new ComputeResource. UUIDs are autoassigned.

        :param request: The request object.
        :type request:
        :return: The response object.
        :rtype:
        ---

        serializer: ComputeResourceSerializer
        """

        return super(ComputeResourceCreate, self).post(request)


class JobView(JSONView):
    class Meta:
        model = Job
        serializer = JobSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # TODO: Only the user that created the job should be able to view
    # and modify the job
    # permission_classes = (DjangoObjectPermissions,)

    def get(self, request, job_id):
        """
        Returns info about a Job, specified by Job ID (UUID).

        :param request: The request object.
        :type request:
        :param job_id: The URL-encoded UUID.
        :type job_id: str
        :return: The response object.
        :rtype:
        ---

        serializer: JobSerializer
        """
        obj = self.get_obj(job_id)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.Meta.serializer(obj)

        # override the DRF output to represent the compute_resource
        # as a UUID string
        data = dict(serializer.data)
        if obj.compute_resource:
            data.update(compute_resource=obj.compute_resource.id)

        if obj.status == Job.STATUS_COMPLETE:
            data.update(result_urls=self._generate_s3_download_urls(obj.id))

        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, job_id):
        """

        PATCH: https://tools.ietf.org/html/rfc5789

        :param request:
        :type request:
        :param job_id:
        :type job_id:
        :return:
        :rtype:
        ---

        serializer: JobSerializer
        """

        job = self.get_obj(job_id)
        if job is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.Meta.serializer(job,
                                          data=request.data,
                                          partial=True)
        if serializer.is_valid():

            # Providing only an exit_code sets job status
            job_status = serializer.validated_data.get('status', None)
            exit_code = serializer.validated_data.get('exit_code', None)
            if job_status is None and exit_code is not None:
                if exit_code == 0:
                    serializer.validated_data.update(status=Job.STATUS_COMPLETE)
                else:
                    serializer.validated_data.update(status=Job.STATUS_FAILED)

            serializer.save()

            job = self.get_obj(job_id)
            if (job.done and
                job.compute_resource and
                job.compute_resource.disposable and
                not job.compute_resource.running_jobs()):
                    task_data = dict(job_id=job_id)
                    tasks.stop_cluster.apply_async(args=(task_data,))

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, job_id):
        """

        :param request:
        :type request:
        :param job_id:
        :type job_id:
        :return:
        :rtype:
        ---

        serializer: JobSerializer
        """
        job = self.get_obj(job_id)
        if job is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if job.compute_resource.disposable:
            task_data = dict(job_id=job_id)
            tasks.stop_cluster.apply_async(args=(task_data,))

        job.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _generate_s3_download_urls(self, job_id,
                                   subpath='input/final',
                                   expires_in=getattr(settings,
                                       'PRESIGNED_S3_URL_TTL', None)):
        """
        For a completed job, generates a set of expiring pre-signed
        S3 download URLs, to be passed to a third party application
        that wants to download the job output.

        :param job_id: The Job UUID
        :type job_id: str
        :param subpath: The relative path inside the job (pseduo)=-)directory
                        (eg under {bucket}/{job_id}/)
        :type subpath: str
        :param expires_in: Expiry time, in seconds from 'now'.
        :type expires_in: datetime.datetime
        :return:
        :rtype:
        """
        subpath = subpath.lstrip('/').rstrip('/')
        path = '%s/%s/' % (job_id, subpath)
        args = (settings.S3_BUCKET,
                path,
                settings.PRESIGNED_S3_URL_TTL)
        # result = tasks.generate_s3_download_urls.apply_async(args=args))
        # Blocking call, since this usually seems fast enough that is doesn't
        # need to be queued
        result = tasks.generate_s3_download_urls.apply(args=args)
        return result.get()


class JobCreate(JSONView):
    class Meta:
        model = Job
        serializer = JobSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    def _munge_sample_descriptions(self, job):
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

    def _get_bcbio_run_job_env(self, job):
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
            self._munge_sample_descriptions(job)

        return {
            'UPDATE_TOOLS': sh_bool(True),
            'UPDATE_DATA': sh_bool(False),
            'MERGE_FILES': sh_bool(merge_files),
            'DOCKER_IMAGE': settings.BCBIO_DOCKER_IMAGE,
        }

    def _get_bcbio_task_data(self, job):
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

    # TODO: This error handler should be used when the job start
    #       task chain fails
    # @shared_task(bind=True)
    # def _task_err_handler(self, task_data):
    #     job_id = task_data.get('job_id', None)
    #     job = Job.objects.get(id=job_id)
    #     job.status = Job.STATUS_FAILED
    #     job.save()
    #
    #     if job.compute_resource and job.compute_resource.disposable:
    #         tasks.stop_cluster.apply_async(
    #             args=({'compute_resource_id': job_id},))

    @method_decorator(csrf_exempt)
    def post(self, request):
        """
        Create a new Job. UUIDs are autoassigned.

        :param request: The request object.
        :type request:
        :return: The response object.
        :rtype:
        ---

        serializer: JobSerializer

        parameters:
            - name: input_files
              description: A JSON list of Files objects.
              required: true
              type: File
              paramType: $ref
        """
        request._dont_enforce_csrf_checks = True

        serializer = JobSerializer(data=request.data)
        if serializer.is_valid():

            job = serializer.save()

            if not job.compute_resource:
                compute = ComputeResource(
                    gateway_server=settings.CLUSTER_MANAGEMENT_HOST)
                compute.save()
                job.compute_resource = compute
                job.save()

            job_id = job.id

            # HACK: TEsting
            # job_id = '1ddIMaKJ9PY8Kug0dW1ubO'

            # callback_url = request.build_absolute_uri(
            #     reverse('laxy_backend:job', args=[job_id]))
            # the request header called "Authorization"
            auth_token = request.META.get(
                'HTTP_AUTHORIZATION',
                get_jwt_user_header_dict(request.user.username))

            # TODO: The location of this template should be defined in settings
            #       It's a jinja2 template that lives on the Django host.
            #       We should also pass in a dictionary of values here to fill
            #       out the template (derived from settings and/or based on
            #       job params) and make a tmp copy, which is the actual path
            #       we pass in as config_template.
            #       Inside cfncluster.start_cluster, we should copy this config
            #       file to the cluster management host and use it.
            default_cluster_config = os.path.expanduser('~/.cfncluster/config')

            port = request.META.get('SERVER_PORT', 8001)
            # domain = get_current_site(request).domain
            # public_ip = requests.get('https://api.ipify.org').text
            callback_url = (u'{scheme}://{domain}:{port}/api/v1/job/{job_id}/'
                            .format(scheme=request.scheme,
                                    domain=PUBLIC_IP,
                                    port=port,
                                    job_id=job_id))

            # better alternative to test
            # callback_url = reverse('job', args=[job_id])

            # Create a JWT object-level access token
            # Authorization: Bearer bl4F00l33th4x0r
            # callback_auth_header = '%s: %s' % make_jwt_header_dict(
            #     create_object_access_jwt(job)).items().pop()

            job_bot, _ = User.objects.get_or_create(username='job_bot')
            token, _ = Token.objects.get_or_create(user=job_bot)
            callback_auth_header = 'Authorization: Token %s' % token.key

            task_data = dict(job_id=job_id,
                             compute_resource_id=job.compute_resource.id,
                             config_template=default_cluster_config,
                             gateway=settings.CLUSTER_MANAGEMENT_HOST,
                             environment={'SCHEDULER': u'slurm_simple',
                                          'JOB_COMPLETE_CALLBACK_URL':
                                              callback_url,
                                          'JOB_COMPLETE_AUTH_HEADER':
                                              callback_auth_header,
                                          })

            task_data['environment'].update(self._get_bcbio_run_job_env(job))
            task_data.update(self._get_bcbio_task_data(job))

            s3_location = 's3://{bucket}/{job_id}/{s3_path}'.format(
                bucket=settings.S3_BUCKET,
                job_id=job_id,
                s3_path='input',
            )

            task_data.update(s3_location=s3_location)

            # TESTING: Just the upload tasks
            # tasks.create_job_object_store.apply_async(args=(task_data,))
            # tasks.upload_input_data_to_object_store.apply_async(args=(task_data,))

            # TESTING: Just starting the cluster
            # tasks.start_cluster.apply_async(args=(task_data,))

            # TESTING: Start cluster, run job, (pre-existing data), stop cluster
            # tasks.run_job_chain(task_data)

            # TESTING:
            # task_data.update(master_ip='52.62.13.233')

            # TESTING: make cluster non-disposable
            # job.compute_resource.disposable = False
            # job.compute_resource.save()

            result = chain(tasks.create_job_object_store.s(task_data),
                           tasks.upload_input_data_to_object_store.s(),
                           tasks.start_cluster.s(),
                           tasks.start_job.s(),
                           # webhook called by job when it completes
                           # or periodic task should stop cluster
                           # when required
                           # tasks.stop_cluster.s()
                           ).apply_async()
                          # TODO: Make this error handler work.
                          #.apply_async(link_error=self._task_err_handler.s())

            # Update the representation of the compute_resource to the uuid,
            # otherwise it is serialized to 'ComputeResource object'
            serializer.validated_data.update(
                compute_resource=job.compute_resource.id)
            # apparently validated_data doens't include this (if it's flagged
            # read-only ?), so we add it back
            serializer.validated_data.update(id=job.id)

            return Response(serializer.validated_data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _get_or_create_drf_token(user):
    token_query = Token.objects.filter(user=user)
    if token_query.exists():
        token = token_query.first()
    else:
        token = Token.objects.create(user=user)

    return token


@login_required()
def view_user_profile(request):
    token = _get_or_create_drf_token(request.user)

    jwt_token = get_jwt_user_header_dict(request.user.username)['Authorization']
    drf_token = 'Token %s' % token.key

    return JsonResponse({'Authorization': [jwt_token, drf_token]})


@login_required()
def show_jwt(request):
    return JsonResponse(get_jwt_user_header_dict(request.user.username))

# def _test_celery_task():
#     from celery import Celery
#     from .tasks import count_words_at_url
#     from django.conf import settings
#     url = 'https://archive.org/stream/AtlasShrugged/atlas%20shrugged_djvu.txt'
#     async_result = count_words_at_url.apply_async(args=(url,),
#                                                   kwargs={},
#                                                   countdown=1)
#     print(async_result.id)
#
#     # we can retrieve the result by UUID ('future') from anywhere
#     app = Celery(settings.BROKER_URL)
#     print(app.AsyncResult(async_result.id).id)
#
#     # an get the result, blocking until ready, or timeout is reached
#     print(async_result.get(timeout=30))
