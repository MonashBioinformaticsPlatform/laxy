from typing import Dict, List
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
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import Http404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from rest_framework import generics
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser

from rest_framework.response import Response
from rest_framework.request import Request
from django.http import HttpResponse
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
from django.utils.encoding import force_text
import coreschema
import coreapi
from rest_framework.filters import BaseFilterBackend
from drf_openapi.utils import view_config

from celery import shared_task
from celery import chain, group

import reversion

from braces.views import LoginRequiredMixin, CsrfExemptMixin

from .jwt_helpers import get_jwt_user_header_dict, create_jwt_user_token
from .models import Job, ComputeResource, File, FileSet, SampleSet, PipelineRun
from .serializers import (PatchSerializerResponse,
                          PutSerializerResponse,
                          JobSerializerResponse,
                          JobSerializerRequest,
                          ComputeResourceSerializer,
                          FileSerializer,
                          FileSerializerPostRequest,
                          FileSetSerializer,
                          FileSetSerializerPostRequest,
                          SampleSetSerializer,
                          PipelineRunSerializer,
                          PipelineRunCreateSerializer,
                          SchemalessJsonResponseSerializer)

from . import tasks
from .tasks import orchestration
from . import ena
from . import bcbio
from .util import sh_bool
from .view_mixins import (JSONView, GetMixin, PatchMixin,
                          DeleteMixin, PostMixin, CSVTextParser, PutMixin)

logger = logging.getLogger(__name__)

PUBLIC_IP = requests.get('http://api.ipify.org').text


# TODO: Strangley, Swagger/CoreAPI only show the 'name' for the query parameter
#       if name='query'. Any other value doesn't seem to appear in the
#       auto-generated docs when applying this as a filter backend as intended
class QueryParamFilterBackend(BaseFilterBackend):
    """
    This class largely exists so that query parameters can appear in the automatic documentation.

    A subclass is used in a DRF view like:

        filter_backends = (CustomQueryParamFilterBackend,)

    to specify the name, description and type of query parameters.

    eg http://my_url/?query=somestring

    To define query params subclass it and pass a list of dictionaries into the superclass constructor like:

    class CustomQueryParams(QueryParamFilterBackend):
        def __init__(self):
            super().__init__([{name: 'query',
                               description: 'A comma separated list of something.'}])

    """

    def __init__(self, query_params: List[Dict[str, any]] = None):

        if query_params is None:
            query_params = []

        for qp in query_params:
            field = coreapi.Field(
                name=qp.get('name'),
                location=qp.get('location', qp.get('name')),
                description=qp.get('description', None),
                example=qp.get('example', None),
                required=qp.get('required', True),
                type=qp.get('type', 'string'),
                schema=coreschema.String(
                    title=force_text(qp.get('title', (qp.get('name', False) or qp.get('name')))),
                    description=force_text(qp.get('description', '')))
            )

            if hasattr(self, 'schema_fields'):
                self.schema_fields.append(field)
            else:
                self.schema_fields = [field]

    def get_schema_fields(self, view):
        return self.schema_fields


class ENAQueryParams(QueryParamFilterBackend):
    def __init__(self):
        super().__init__([
            dict(name='accessions',
                 example='PRJNA276493,SRR950078',
                 description='A comma separated list of ENA/SRA accessions.'),
        ])


class ENAQueryView(APIView):
    renderer_classes = (JSONRenderer,)
    serializer_class = SchemalessJsonResponseSerializer
    # TODO: Would this be better achieved with a SearchFilter ?
    # http://www.django-rest-framework.org/api-guide/filtering/#searchfilter
    filter_backends = (ENAQueryParams,)
    api_docs_visible_to = 'public'

    @view_config(response_serializer=SchemalessJsonResponseSerializer)
    def get(self, request, version=None):
        """
        Queries ENA metadata. Essentially a proxy for ENA REST API
        requests by accession, converting the XML output to JSON
        (eg https://www.ebi.ac.uk/ena/data/view/SRR950078&display=xml).

        Returns JSON equivalent to the ENA response.

        Query parameters:

        * `accessions` - a comma seperated list of ENA accessions

        <!--
        :param request:
        :type request:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """
        accession_list = request.query_params.get('accessions', None)
        if accession_list is not None:
            accessions = accession_list.split(',')
            ena_result = ena.search_ena_accessions(accessions)

            return Response(ena_result, status=status.HTTP_200_OK)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class ENAFastqUrlQueryView(JSONView):
    renderer_classes = (JSONRenderer,)
    serializer_class = SchemalessJsonResponseSerializer
    filter_backends = (ENAQueryParams,)
    api_docs_visible_to = 'public'

    @view_config(response_serializer=SchemalessJsonResponseSerializer)
    def get(self, request, version=None):
        """
        Returns a JSON object contains study, experiment, run and sample
        accessions associated with a given ENA accession, as well as the
        FASTQ FTP download links, md5 checksum, size and read count.

        Query parameters:

        * `accessions` - a comma separated list of ENA accessions

        <!--
        :param request:
        :type request:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """
        accession_list = request.query_params.get('accessions', None)
        if accession_list is not None:
            accessions = accession_list.split(',')
            # ena_result = ena.get_fastq_urls(accessions)
            ena_result = ena.get_run_table(accessions)

            return Response(ena_result, status=status.HTTP_200_OK)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)


class FileCreate(JSONView):
    class Meta:
        model = File
        serializer = FileSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(request_serializer=FileSerializerPostRequest,
                 response_serializer=FileSerializer)
    # @method_decorator(csrf_exempt)
    def post(self, request: Request, version=None):
        """
        Create a new File. UUIDs are autoassigned.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        serializer = self.Meta.serializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileView(GetMixin,
               DeleteMixin,
               PatchMixin,
               PutMixin,
               JSONView):
    class Meta:
        model = File
        serializer = FileSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=FileSerializer)
    def get(self, request: Request, uuid=None, version=None):
        """
        Returns info about a File, specified by UUID.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        return super(FileView, self).get(request, uuid)

    @view_config(request_serializer=FileSerializer,
                 response_serializer=PatchSerializerResponse)
    def patch(self, request, uuid=None, version=None):
        return super(FileView, self).patch(request, uuid)

    @view_config(request_serializer=FileSerializerPostRequest,
                 response_serializer=FileSerializer)
    def put(self, request: Request, uuid: str, version=None):
        """
        Replace the content of an existing File.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        return super(FileView, self).put(
            request,
            uuid,
            serializer_class=FileSerializerPostRequest)


class FileSetCreate(PostMixin,
                    JSONView):
    class Meta:
        model = FileSet
        serializer = FileSetSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(request_serializer=FileSetSerializerPostRequest,
                 response_serializer=FileSetSerializer)
    # @method_decorator(csrf_exempt)
    def post(self, request: Request, version=None):
        """
        Create a new FileSet. UUIDs are autoassigned.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        return super(FileSetCreate, self).post(request)


class FileSetView(GetMixin,
                  DeleteMixin,
                  PatchMixin,
                  JSONView):
    class Meta:
        model = FileSet
        serializer = FileSetSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=FileSetSerializer)
    def get(self, request: Request, uuid, version=None):
        """
        Returns info about a FileSet, specified by UUID.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        return super(FileSetView, self).get(request, uuid)

    @view_config(request_serializer=FileSetSerializer,
                 response_serializer=PatchSerializerResponse)
    def patch(self, request, uuid, version=None):
        return super(FileSetView, self).patch(request, uuid)


class SampleSetCreateUpdate(JSONView):
    class Meta:
        model = SampleSet
        serializer = SampleSetSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer
    parser_classes = (JSONParser, MultiPartParser, CSVTextParser,)

    def create_update(self, request, obj):
        """
        Replaces an existing SampleSet with new content, or creates a new one if `uuid` is None.

        :param obj:
        :type obj:
        :param request:
        :type request:
        :return:
        :rtype:
        """

        content_type = request.content_type.split(';')[0].strip()
        encoding = 'utf-8'

        if content_type == 'multipart/form-data':
            fh = request.data.get('file', None)
            csv_table = fh.read().decode(encoding)
            obj.from_csv(csv_table)

            return Response(self.Meta.serializer(obj).data, status=status.HTTP_200_OK)

        elif content_type == 'text/csv':
            csv_table = request.data
            obj.from_csv(csv_table)

            return Response(self.Meta.serializer(obj).data, status=status.HTTP_200_OK)

        elif content_type == 'application/json':
            serializer = self.Meta.serializer(obj, data=request.data)
            if serializer.is_valid():
                obj = serializer.save(owner=request.user)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(None, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)


class SampleSetCreate(SampleSetCreateUpdate):

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(request_serializer=SampleSetSerializer,
                 response_serializer=SampleSetSerializer)
    # @method_decorator(csrf_exempt)
    def post(self, request: Request, version=None):
        """
        Create a new SampleSet. UUIDs are autoassigned.

        `samples` is an object keyed by sample name, with a list of files grouped by
        'merge group' and pair (a 'merge group' could be a set of equivalent lanes the sample
        was split across, or a technical replicate):

        Equivalent samples (technical replicates) in different lanes can be merged -
        they could also be thought of as split FASTQ files.

        Several content-types are supported:

          - `application/json` (accepting JSON objects below)
          - `text/csv` where the POST body is CSV text as in: https://tools.ietf.org/html/rfc4180
          - `multipart/form-data` where the `file` field is the CSV file.

        CSV example:

        ```csv
        SampleA,ftp://bla_lane1_R1.fastq.gz,ftp://bla_lane1_R2.fastq.gz
        SampleA,ftp://bla_lane2_R1.fastq.gz,ftp://bla_lane2_R2.fastq.gz
        SampleB,ftp://bla2_R1_001.fastq.gz,ftp://bla2_R2_001.fastq.gz
               ,ftp://bla2_R1_002.fastq.gz,ftp://bla2_R2_002.fastq.gz
        SampleC,ftp://foo2_lane4_1.fastq.gz,ftp://foo2_lane4_2.fastq.gz
        SampleC,ftp://foo2_lane5_1.fastq.gz,ftp://foo2_lane5_2.fastq.gz
        ```

        Columns are sampleName, R1 file, R2 file.
        Repeated sample names represent 'merge groups' (eg additional lanes containing techinal replicates).

        JSON request body example:

        A single 'sampleName' actually corresponds to a Sample+Condition+BiologicalReplicate.

        For two samples (R1, R2 paired end) split across two lanes, using File UUIDs:

        ```json
        {
            "name": "My New Sample Set",
            "samples": [
                {
                    "name": "sample_wildtype",
                    files: [
                        {
                            "R1": "2VSd4mZvmYX0OXw07dGfnV",
                            "R2": "3XSd4mZvmYX0OXw07dGfmZ"
                        },
                        {
                            "R1": "Toopini9iPaenooghaquee",
                            "R2": "Einanoohiew9ungoh3yiev"
                        }]
                },
                {
                    "name": "sample_mutant",
                    "files": [
                        {
                            "R1": "zoo7eiPhaiwion6ohniek3",
                            "R2": "ieshiePahdie0ahxooSaed"
                        },
                        {
                            "R1": "nahFoogheiChae5de1iey3",
                            "R2": "Dae7leiZoo8fiesheech5s"
                        }]
                }
            ]
        }
        ```

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        sample_name = request.data.get('name', 'CSV uploaded on %s' % datetime.isoformat(datetime.now()))
        obj = self.Meta.model(name=sample_name, owner=request.user)
        return self.create_update(request, obj)


class SampleSetView(GetMixin,
                    DeleteMixin,
                    SampleSetCreateUpdate):

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=SampleSetSerializer)
    def get(self, request: Request, uuid, version=None):
        """
        Returns info about a FileSet, specified by UUID.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        return super(SampleSetView, self).get(request, uuid)

    @view_config(request_serializer=SampleSetSerializer,
                 response_serializer=PutSerializerResponse)
    def put(self, request, uuid, version=None):
        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if 'id' in request.data:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="id cannot be updated")

        sample_name = request.data.get('name', None)
        if sample_name is not None:
            obj.name = sample_name

        return self.create_update(request, obj)

    # TODO: CSV upload doesn't append/merge, it aways creates a new SampleSet.
    #       Implement PATCH method so we can append/merge an uploaded CSV rather
    #       than just replace wholesale
    #
    # @view_config(request_serializer=SampleSetSerializer,
    #              response_serializer=PatchSerializerResponse)
    # def patch(self, request, uuid, version=None):
    #     return super(SampleSetView, self).patch(request, uuid)


class ComputeResourceView(GetMixin,
                          DeleteMixin,
                          JSONView):
    class Meta:
        model = ComputeResource
        serializer = ComputeResourceSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer
    permission_classes = (IsAdminUser,)

    def get(self, request: Request, uuid, version=None):
        """
        Returns info about a ComputeResource, specified by UUID.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        return super(ComputeResourceView, self).get(request, uuid)

    @view_config(request_serializer=ComputeResourceSerializer,
                 response_serializer=PatchSerializerResponse)
    def patch(self, request: Request, uuid, version=None):
        """
        Updates a ComputeResource record. Since this is a PATCH request,
        partial updates are allowed.

        **Side effect:** for disposable compute resources changing
        `status` to `decommissioned` or `terminating` will
        shutdown / terminate this resource so it is no longer available.

        <!--
        :param request:
        :type request: rest_framework.request.Request
        :param uuid: The compute resource UUID.
        :type uuid: str
        :return:
        :rtype: rest_framework.response.Response
        -->
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
                obj.dispose()

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

    @view_config(request_serializer=ComputeResourceSerializer,
                 response_serializer=ComputeResourceSerializer)
    # @method_decorator(csrf_exempt)
    def post(self, request: Request, version=None):
        """
        Create a new ComputeResource. UUIDs are autoassigned.

        The `extra` field is a JSON object. Attributes may include:
          * `username` - the login name to access the ComputeResource
          * `private_key` - a Base64 encoded SSH private key (eg, generated on
          the commandline like `base64 < ~/.ssh/id_rsa`).
          * `base_dir` - the absolute path to where job processing directories
             will be created on the ComputeResource.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        return super(ComputeResourceCreate, self).post(request)


class PipelineRunCreate(PostMixin,
                        JSONView):
    class Meta:
        model = PipelineRun
        serializer = PipelineRunCreateSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(request_serializer=PipelineRunCreateSerializer,
                 response_serializer=PipelineRunSerializer)
    def post(self, request: Request, version=None):
        """
        Create a new PipelineRun. UUIDs are autoassigned.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        return super(PipelineRunCreate, self).post(request)


class PipelineRunView(GetMixin,
                      DeleteMixin,
                      PutMixin,
                      PatchMixin,
                      JSONView):
    class Meta:
        model = PipelineRun
        serializer = PipelineRunSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=PipelineRunSerializer)
    def get(self, request: Request, uuid, version=None):
        """
        Returns info about a FileSet, specified by UUID.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        return super(PipelineRunView, self).get(request, uuid)

    @view_config(request_serializer=PipelineRunSerializer,
                 response_serializer=PipelineRunSerializer)
    def patch(self, request, uuid, version=None):
        return super(PipelineRunView, self).patch(request, uuid)

    @view_config(request_serializer=PipelineRunCreateSerializer,
                 response_serializer=PipelineRunSerializer)
    def put(self, request: Request, uuid: str, version=None):
        """
        Replace the content of an existing PipelineRun.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        return super(PipelineRunView, self).put(
            request,
            uuid,
            serializer_class=PipelineRunCreateSerializer)


class JobView(JSONView):
    class Meta:
        model = Job
        serializer = JobSerializerResponse

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=JobSerializerResponse)
    def get(self, request: Request, job_id, version=None):
        """
        Returns info about a Job, specified by Job ID (UUID).

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param job_id: The URL-encoded UUID.
        :type job_id: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
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
            pass

        return Response(data, status=status.HTTP_200_OK)

    @view_config(request_serializer=JobSerializerRequest,
                 response_serializer=PatchSerializerResponse)
    def patch(self, request: Request, job_id, version=None):
        """

        The main purpose of this endpoint is to update job `status` and `exit_code`.
        Setting `exit_code` automatically updates the job status (zero implies 'complete',
        non-zero is 'failed').

        Note that in some cases updating job `status` may have side-effects beyond
        simply updating the Job record.
        Eg, changing `status` to "complete", "cancelled" or "failed" may terminate the
        associated compute instance if it was a single-job disposable ComputeResource, or
        trigger movement or cleanup of staged / temporary / intermediate files.

        Valid job statuses are "created", "hold", "starting", "running", "failed", "cancelled"
        and "complete".

        <!--
        :param request:
        :type request: rest_framework.request.Request
        :param job_id: The job UUID.
        :type job_id: str
        :return:
        :rtype: rest_framework.response.Response
        -->
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
                job.compute_resource.dispose()

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request: Request, job_id, version=None):
        """

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param job_id: A job UUID.
        :type job_id: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        job = self.get_obj(job_id)
        if job is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if job.compute_resource.disposable:
            task_data = dict(job_id=job_id)
            job.compute_resource.dispose()

        job.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class JobCreate(JSONView):
    class Meta:
        model = Job
        serializer = JobSerializerRequest

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    @shared_task(bind=True)
    def _task_err_handler(failed_task, cxt, ex, tb, job_id):
        # job_id = task_data.get('job_id', None)
        job = Job.objects.get(id=job_id)
        job.status = Job.STATUS_FAILED
        job.save()

        if job.compute_resource and job.compute_resource.disposable:
            job.compute_resource.dispose()

    @view_config(request_serializer=JobSerializerRequest,
                 response_serializer=JobSerializerResponse)
    # @method_decorator(csrf_exempt)
    def post(self, request: Request, version=None):
        """
        Create a new Job. UUIDs are autoassigned.

        If the query parameter `?pipeline_run_id={uuid}` is
        provided, `params` is populated with the serialized
        PipelineRun instance.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        # setattr(request, '_dont_enforce_csrf_checks', True)

        serializer = JobSerializerRequest(data=request.data,
                                          context={'request': request})

        pipeline_run_id = request.query_params.get('pipeline_run_id', None)
        if pipeline_run_id:
            try:
                pipeline_run_obj = PipelineRun.objects.get(id=pipeline_run_id)
            except PipelineRun.DoesNotExist:
                return HttpResponse(reason='pipeline_run %s does not exist'
                                           % pipeline_run_id,
                                    status=status.HTTP_400_BAD_REQUEST)
            request.data['params'] = pipeline_run_obj.to_json()

        if serializer.is_valid():

            job_status = serializer.validated_data.get('status', '')
            if job_status != '' and job_status != Job.STATUS_HOLD:
                return HttpResponse(reason='status can only be set to "%s" '
                                           'or left unset for job creation'
                                           % Job.STATUS_HOLD,
                                    status=status.HTTP_400_BAD_REQUEST)

            job = serializer.save()  # owner=request.user)

            if job.status == Job.STATUS_HOLD:
                return Response(serializer.data, status=status.HTTP_200_OK)

            if not job.compute_resource:
                job.compute_resource = _get_default_compute_resource()
                job.save()

            job_id = job.id

            callback_url = request.build_absolute_uri(
                reverse('laxy_backend:job', args=[job_id]))

            # port = request.META.get('SERVER_PORT', 8001)
            # # domain = get_current_site(request).domain
            # # public_ip = requests.get('https://api.ipify.org').text
            # callback_url = (u'{scheme}://{domain}:{port}/api/v1/job/{job_id}/'.format(
            #     scheme=request.scheme,
            #     domain=PUBLIC_IP,
            #     port=port,
            #     job_id=job_id))

            # job_bot, _ = User.objects.get_or_create(username='job_bot')
            # token, _ = Token.objects.get_or_create(user=job_bot)

            token, _ = Token.objects.get_or_create(user=request.user)
            callback_auth_header = 'Authorization: Token %s' % token.key

            task_data = dict(job_id=job_id,
                             compute_resource_id=job.compute_resource.id,
                             # pipeline_run_config=pipeline_run.to_json(), # this is job.params
                             # gateway=settings.CLUSTER_MANAGEMENT_HOST,
                             environment={'JOB_ID': job_id,
                                          'JOB_COMPLETE_CALLBACK_URL':
                                              callback_url,
                                          'JOB_COMPLETE_AUTH_HEADER':
                                              callback_auth_header,
                                          'JOB_INPUT_STAGED': sh_bool(True),
                                          })

            # TESTING: Start cluster, run job, (pre-existing data), stop cluster
            # tasks.run_job_chain(task_data)

            result = tasks.start_job.apply_async(
                args=(task_data,),
                link_error=self._task_err_handler.s(job_id))
            # Non-async for testing
            # result = tasks.start_job(task_data)

            # result = chain(# tasks.stage_job_config.s(task_data),
            #                # tasks.stage_input_files.s(),
            #                tasks.start_job.s(task_data),
            #                ).apply_async()

            # TODO: Make this error handler work.
            # .apply_async(link_error=self._task_err_handler.s(job_id))

            # Update the representation of the compute_resource to the uuid,
            # otherwise it is serialized to 'ComputeResource object'
            # serializer.validated_data.update(
            #     compute_resource=job.compute_resource.id)

            # apparently validated_data doesn't include this (if it's flagged
            # read-only ?), so we add it back
            # serializer.validated_data.update(id=job.id)

            job = Job.objects.get(id=job_id)
            if result.state == 'FAILURE':
                raise result.result
                # return Response({'error': result.traceback},
                #                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            serializer = JobSerializerResponse(job)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @view_config(request_serializer=JobSerializerRequest,
                 response_serializer=JobSerializerResponse)
    # @method_decorator(csrf_exempt)
    def _cfn_cluster_create_flow(self, request: Request, version=None):
        serializer = JobSerializerRequest(data=request.data,
                                          context={'request': request})
        if serializer.is_valid():

            job = serializer.save()  # owner=request.user)

            if not job.compute_resource:
                job.compute_resource = _get_default_compute_resource()
                job.save()

            job_id = job.id

            # HACK: Testing
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
            callback_url = (u'{scheme}://{domain}:{port}/api/v1/job/{job_id}/'.format(
                scheme=request.scheme,
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

            task_data['environment'].update(bcbio.get_bcbio_run_job_env(job))
            task_data.update(bcbio.get_bcbio_task_data(job))

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
            # .apply_async(link_error=self._task_err_handler.s())

            # Update the representation of the compute_resource to the uuid,
            # otherwise it is serialized to 'ComputeResource object'
            serializer.validated_data.update(
                compute_resource=job.compute_resource.id)
            # apparently validated_data doesn't include this (if it's flagged
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


def _get_default_compute_resource():
    compute = ComputeResource.objects.filter(
        name=getattr(settings, 'DEFAULT_COMPUTE_RESOURCE')).first()
    compute.save()
    return compute

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
