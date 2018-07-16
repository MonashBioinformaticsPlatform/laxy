import asyncio
from collections import OrderedDict
import coreapi
import coreschema
import json_merge_patch
import jsonpatch
import logging
import os
import requests
import rest_framework_jwt
from celery import chain
from celery import shared_task
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import user_passes_test
from django.db import transaction
from django.http import HttpResponse, StreamingHttpResponse
from django.urls import reverse
from django.utils.encoding import force_text
from django_filters.rest_framework import DjangoFilterBackend
from io import BytesIO
from pathlib import Path
import paramiko
from robobrowser import RoboBrowser
from rest_framework import generics
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (api_view,
                                       renderer_classes,
                                       permission_classes,
                                       authentication_classes)
from rest_framework.filters import BaseFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer, BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import Dict, List, Union
from urllib.parse import urlparse
from wsgiref.util import FileWrapper

from drf_openapi.utils import view_config
from . import bcbio
from . import ena
from . import tasks
from .jwt_helpers import (get_jwt_user_header_dict,
                          get_jwt_user_header_str)
from .models import (Job,
                     ComputeResource,
                     File,
                     FileSet,
                     SampleSet,
                     PipelineRun,
                     EventLog)
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
                          SchemalessJsonResponseSerializer,
                          JobListSerializerResponse,
                          EventLogSerializer, JobEventLogSerializer,
                          JobFileSerializerCreateRequest, InputOutputFilesResponse, RedirectResponseSerializer)
from .util import sh_bool, laxy_sftp_url
from .view_mixins import (JSONView, GetMixin, PatchMixin,
                          DeleteMixin, PostMixin, CSVTextParser, PutMixin, RowsCSVTextParser)

# from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

PUBLIC_IP = requests.get('http://api.ipify.org').text

# This maps reference identifiers, sent via web API requests, to a relative path containing
# the reference genome (iGenomes directory structure), like {id: path}.
# TODO: This should be a default config somewhere, pipeline/plugin specific.
#       Each compute resource should be able to override this setting.
REFERENCE_GENOME_MAPPINGS = {
    "Homo_sapiens/Ensembl/GRCh37": "Homo_sapiens/Ensembl/GRCh37",
    "Homo_sapiens/UCSC/hg19": "Homo_sapiens/UCSC/hg19",
    "Homo_sapiens/NCBI/build37.2": "Homo_sapiens/NCBI/build37.2",

    "Mus_musculus/UCSC/mm10": "Mus_musculus/UCSC/mm10",
    "Mus_musculus/Ensembl/GRCm38": "Mus_musculus/Ensembl/GRCm38",
    "Mus_musculus/NCBI/GRCm38": "Mus_musculus/NCBI/GRCm38",

    "Saccharomyces_cerevisiae/Ensembl/R64-1-1": "Saccharomyces_cerevisiae/Ensembl/R64-1-1",
    # "Saccharomyces_cerevisiae/UCSC/sacCer3": "Saccharomyces_cerevisiae/UCSC/sacCer3",
    # "Saccharomyces_cerevisiae/NCBI/build3.1": "Saccharomyces_cerevisiae/NCBI/build3.1",

    "Caenorhabditis_elegans/Ensembl/WBcel235": "Caenorhabditis_elegans/Ensembl/WBcel235",
    "Caenorhabditis_elegans/UCSC/ce10": "Caenorhabditis_elegans/UCSC/ce10",
    "Caenorhabditis_elegans/NCBI/WS195": "Caenorhabditis_elegans/NCBI/WS195",
}


def get_content_type(request: Request) -> str:
    """
    Returns the simple Content-Type (MIME type/media type) for an HTTP Request
    object.

    :param request: The request.
    :type request: Request
    :return: The content type, eg text/html or application/json
    :rtype: str
    """
    return request.content_type.split(';')[0].strip()


# TODO: Strangley, Swagger/CoreAPI only show the 'name' for the query parameter
#       if name='query'. Any other value doesn't seem to appear in the
#       auto-generated docs when applying this as a filter backend as intended
class QueryParamFilterBackend(BaseFilterBackend):
    """
    This class largely exists so that query parameters can appear in the
    automatic documentation.

    A subclass is used in a DRF view like:

        filter_backends = (CustomQueryParamFilterBackend,)

    to specify the name, description and type of query parameters.

    eg http://my_url/?query=somestring

    To define query params subclass it and pass a list of dictionaries into the
    superclass constructor like:

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
                    title=force_text(qp.get('title', (qp.get('name', False)
                                                      or qp.get('name')))),
                    description=force_text(qp.get('description', '')))
            )

            if hasattr(self, 'schema_fields'):
                self.schema_fields.append(field)
            else:
                self.schema_fields = [field]

    def get_schema_fields(self, view):
        return self.schema_fields


class StreamingFileDownloadRenderer(BaseRenderer):
    media_type = 'application/octet-stream'
    format = 'download'
    charset = None
    render_style = 'binary'

    def render(self, filelike, media_type=None, renderer_context=None,
               blksize=8192):
        iterable = FileWrapper(filelike, blksize=blksize)
        for chunk in iterable:
            yield chunk


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


class JSONPatchRFC7386Parser(JSONParser):
    media_type = 'application/merge-patch+json'


class JSONPatchRFC6902Parser(JSONParser):
    media_type = 'application/json-patch+json'


class StreamFileMixin(JSONView):

    def _as_file_obj(self, obj_ref: Union[str, File]):
        """
        Convert a File UUID string to a File instance, if required.
        """

        if isinstance(obj_ref, str):
            obj = self.get_obj(obj_ref)
        else:
            obj = obj_ref

        return obj

    def _add_metalink_headers(self, obj, response):

        url = self.request.build_absolute_uri(obj.get_absolute_url())
        response['Link'] = f'<{url}>; rel=duplicate'

        if hasattr(obj, 'checksum') and obj.checksum:
            hashtype = obj.checksum_type
            b64checksum = obj.checksum_hash_base64
            response['Digest'] = f'{hashtype.upper()}={b64checksum}'
            response['Etag'] = f'{obj.checksum}'

        return response

    def _stream_response(
            self,
            obj_ref: Union[str, File],
            filename: str = None,
            download: bool = True) -> Union[StreamingHttpResponse, Response]:

        obj = self._as_file_obj(obj_ref)

        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        renderer = StreamingFileDownloadRenderer()
        # TODO: For local file:// URLs, django.http.response.FileResponse
        #       will probably preform better
        response = StreamingHttpResponse(
            renderer.render(obj.file),
            content_type=StreamingFileDownloadRenderer.media_type)

        # A filename can optionally be specified in the URL, so that
        # wget will 'just work' without requiring the --content-disposition
        # flag, eg:
        # wget http://laxy.org/api/v1/file/XXblafooXX/alignment.bam
        # vs.
        # wget --content-disposition http://laxy.org/api/v1/file/XXblafooXX/
        #
        if filename is not None:
            if filename != obj.name:
                return Response(status=status.HTTP_404_NOT_FOUND)

        if download:
            response['Content-Disposition'] = f'attachment; filename="{obj.name}"'
        else:
            response['Content-Disposition'] = 'inline'
            # Make the browser guess the Content-Type
            del response['Content-Type']

        size = obj.metadata.get('size', None)
        if size is not None:
            response['Content-Length'] = int(size)

        self._add_metalink_headers(obj, response)

        return response

    def download(self, obj_ref: Union[str, File], filename=None):
        obj = self._as_file_obj(obj_ref)
        return self._stream_response(obj, filename, download=True)

    def view(self, obj_ref: Union[str, File], filename=None):
        obj = self._as_file_obj(obj_ref)
        return self._stream_response(obj, filename, download=False)


class FileContentDownload(StreamFileMixin,
                          GetMixin,
                          JSONView):
    class Meta:
        model = File
        serializer = FileSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=FileSerializer)
    def get(self, request: Request, uuid=None, filename=None, version=None):
        """
        Downloads the content of a File.

        When using a web browser, if the query parameter `download` is included
        the file will be downloaded rather than viewed in a new tab
        (via the `Content-Disposition: attachment` header).

        If file checksums (eg MD5) are present, these are included as a
        header:

        `Digest: MD5=thisIsABase64EnC0DeDMd5sum==`.

        A filename can optionally be specified as the last part of the the URL
        path, so that `wget` will 'just work' without requiring the
        `--content-disposition` flag. The filename must match the name stored
        in the File record.

        Examples:

        ### File content (view in browser)

        **Request:**

        `Content-Type: application/octet-stream`

        `GET` http://laxy.org/api/v1/file/XXblafooXX/content/alignment.bam

        **Response:**

        Headers:

        `Content-Disposition: inline`

        `Digest: MD5=thisIsABase64EnC0DeDMd5sum==`

        Body:

        .. file content ..

        ### File content (download in browser)

        **Request:**

        `Content-Type: application/octet-stream`

        `GET` http://laxy.org/api/v1/file/XXblafooXX/content/alignment.bam?download

        **Response:**

        Headers:

        `Content-Disposition: attachment; filename=alignment.bam`

        `Digest: MD5=thisIsABase64EnC0DeDMd5sum==`

        Body:

        .. file content ..


        ## File download with `wget`

        `wget http://laxy.org/api/v1/file/XXblafooXX/content/alignment.bam`

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        # File view/download is the default when no Content-Type is specified
        if 'download' in request.query_params:
            return super().download(uuid, filename=filename)
        else:
            return super().view(uuid, filename=filename)


class FileView(StreamFileMixin,
               GetMixin,
               DeleteMixin,
               PatchMixin,
               PutMixin,
               JSONView):
    class Meta:
        model = File
        serializer = FileSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer
    parser_classes = (JSONParser,
                      JSONPatchRFC7386Parser,
                      JSONPatchRFC6902Parser)

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=FileSerializer)
    def get(self, request: Request, uuid=None, filename=None, version=None):
        """
        Returns info about a file or downloads the content.
        File is specified by it's UUID.

        If the `Content-Type: application/json` header is used, the
        JSON record for the file is returned.

        Other `Content-Type`s return the content of the file.

        See the [file/{uuid}/content/ docs](#operation/v1_file_content_read) for
        details about file content downloads (this endpoint behaves the same with
        regard to downloads, except that the filename is omitted from the URL)

        Examples:

        ### File record data as JSON

        **Request:**

        `Content-Type: application/json`

        `GET` http://laxy.org/api/v1/file/XXblafooXX/content/alignment.bam

        **Response:**

        ```json
        {
            "id": "XXblafooXX",
            "name": "alignment.bam",
            "location": "http://example.com/datasets/1/alignment.bam",
            "owner": "admin",
            "checksum": "md5:f3c90181aae57b887a38c4e5fe73db0c",
            "type_tags": ['bam', 'bam.sorted', 'alignment']
            "metadata": { }
        }
        ```

        To correctly set the filename:

        `wget --content-disposition http://laxy.org/api/v1/file/XXblafooXX/`


        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        content_type = get_content_type(request)
        if content_type == 'application/json':
            return super().get(request, uuid)
        else:
            # File view/download is the default when no Content-Type is specified
            try:
                if 'download' in request.query_params:
                    return super().download(uuid, filename=filename)
                else:
                    return super().view(uuid, filename=filename)
            except (paramiko.ssh_exception.AuthenticationException,
                    paramiko.ssh_exception.SSHException) as ex:
                return HttpResponse(
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    reason="paramiko.ssh_exception.AuthenticationException")

    def _try_json_patch(self, request, uuid):
        content_type = get_content_type(request)
        if content_type in ['application/merge-patch+json',
                            'application/json-patch+json']:
            obj = self.get_obj(uuid)
            if obj is None:
                return Response(status=status.HTTP_404_NOT_FOUND)

            if 'id' in request.data:
                return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                    reason="id cannot be updated")

            metadata = request.data.get('metadata', None)
            if metadata is not None:
                if isinstance(metadata, list):
                    patch = [OrderedDict(op) for op in metadata]
                else:
                    patch = OrderedDict(metadata)

                # https://tools.ietf.org/html/rfc7386
                if content_type == 'application/merge-patch+json':
                    request.data['metadata'] = json_merge_patch.merge(
                        OrderedDict(obj.metadata),
                        patch)
                # https://tools.ietf.org/html/rfc6902
                if content_type == 'application/json-patch+json':
                    request.data['metadata'] = jsonpatch.apply_patch(
                        OrderedDict(obj.metadata),
                        patch)

            serializer = self.Meta.serializer(obj,
                                              data=request.data,
                                              context={'request': request},
                                              partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

        return None

    @view_config(request_serializer=FileSerializer,
                 response_serializer=PatchSerializerResponse)
    def patch(self, request, uuid=None, version=None):
        """
        Partial update of fields on File.

        If the header `Content-Type: application/merge-patch+json` is set,
        the `metadata` field is patched as per the specification in
        [RFC 7386](https://tools.ietf.org/html/rfc7386). eg, if the existing
        metadata was:

        ```json
        {"metadata": {"tags": ["A"], "name": "seqs.fastq.gz", "path": "/tmp"}}
        ```

        The patch in a request:

        ```json
        {"metadata": {"tags": ["B", "C"], "path": null}}
        ```

        Would change it to:

        ```json
        {"metadata": {"tags": ["B", "C"], "name": "seqs.fastq.gz"}}
        ```

        If `Content-Type: application/json-patch+json` is set, `metadata`
        should be an array of mutation operations to apply as per
        [RFC 6902](https://tools.ietf.org/html/rfc6902).

        <!--
        :param request:
        :type request:
        :param uuid:
        :type uuid:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """

        resp = self._try_json_patch(request, uuid)
        if resp is not None:
            return resp

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


class JobFileView(StreamFileMixin,
                  GetMixin,
                  JSONView):
    class Meta:
        model = Job
        serializer = FileSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer
    parser_classes = (JSONParser,)

    @view_config(response_serializer=FileSerializer)
    def get(self,
            request: Request,
            job_id: str,
            file_path: str,
            version=None):
        """
        Get a `File` by path, associated with this `Job`.

        See the documentation for [file/{uuid}/content/ docs](#operation/v1_file_content_read)
        endpoints for a description on how `Content-Types` and the `?download`
        query strings are handled (JSON response vs. download vs. view).

        Valid values for `file_path` are:

         - `input`
         - `output`

        corresponding to the input and output FileSets respectively.

        <!--
        :param request:
        :type request:
        :param job_id:
        :type job_id:
        :param file_path:
        :type file_path:
        :return:
        :rtype:
        -->
        """
        job = self.get_obj(job_id)
        if job is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        fname = Path(file_path).name
        fpath = Path(file_path).parent
        file_obj = job.get_files().filter(name=fname, path=fpath).first()
        if file_obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # serializer = self.Meta.serializer(file_obj)
        # return Response(serializer.data, status=status.HTTP_200_OK)

        content_type = get_content_type(request)
        if content_type == 'application/json':
            return super().get(request, file_obj.id)
        else:
            # File view/download is the default when no Content-Type is specified
            if 'download' in request.query_params:
                return super().download(file_obj, filename=fname)
            else:
                return super().view(file_obj, filename=fname)

        # return super(FileView, self).get(request, file_obj.id)

    @transaction.atomic()
    @view_config(request_serializer=JobFileSerializerCreateRequest,
                 response_serializer=FileSerializer)
    def put(self,
            request: Request,
            job_id: str,
            file_path: str,
            version=None):
        """
        Create (or replace) a File record by job ID and path. This endpoint
        is generally intended to be called by the job script on a compute node
        to register files with specific `checksum`, `metadata`, `type_tags`
        and possibly `location` fields.

        `file_path` is the relative path of the file in the job directory. It
        must begin with `input/` or `output/`, corresponding to the input and
        output FileSets.

        Typically you should not set `location` - it is automatically generated
        to be a URL pointing to data accessible on the ComputeResource.

        `location` can be set if your job script manually stages the job files
        to another location (eg, stores outputs in an object store like S3).

        <!--
        :param request:
        :type request:
        :param job_id:
        :type job_id:
        :param file_path:
        :type file_path:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        fname = Path(file_path).name
        fpath = Path(file_path).parent

        fileset_path = fpath.parts[0]

        if fileset_path == 'output':
            fileset = job.output_files
        elif fileset_path == 'input':
            fileset = job.input_files
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Generate a location URL if not set explicitly
        data = dict(request.data)
        data['name'] = fname
        data['path'] = str(fpath)
        location = data.get('location', None)
        if not location:
            data['location'] = laxy_sftp_url(job, f'{fpath}/{fname}')

        elif not urlparse(location).scheme:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="Location must be a valid URL.")

        # TODO: consider how best to handle file:// URLs here
        # file:// URLs could be used in the location field if the job
        # directories are mounted on both the compute node and the server.
        # We could treat them as a path relative to the job directory (given
        # that we know the job here).
        # We need to be careful when creating Files with file:// locations -
        # there is the potential for a tricky user to create locations
        # that point to anywhere on the server filesystem (eg absolute path to
        # /etc/passwd). For the moment they are disallowed here
        if urlparse(location).scheme == 'file':
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="file:// locations are not allowed "
                                       "using this API endpoint.")

            # # we make the path relative, even if there is a leading /
            # cleaned = location.lstrip('file://').lstrip('/')
            # if '../' in cleaned:
            #     return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
            #                         reason="file:// location cannot contain "
            #                                "../ in relative paths.")
            #
            # data['location'] = (f'laxy+file://'
            #                     f'{job.compute_resource.id}/{job_id}/{cleaned}')

        file_obj = fileset.get_files_by_path(file_path).first()
        if file_obj is None:
            # Create new file. Inferred location based on job+compute
            # We actually use the POST serializer to include name and path etc
            serializer = FileSerializerPostRequest(data=data,
                                                   context={'request': request})

            if serializer.is_valid():
                serializer.save()
                fileset.add(serializer.instance, save=True)
                data = self.response_serializer(serializer.instance).data
                return Response(data, status=status.HTTP_201_CREATED)
        else:
            # Update existing File
            serializer = self.request_serializer(
                file_obj,
                data=request.data,
                context={'request': request})

            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_200_OK,
                                data=serializer.validated_data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobFileBulkRegistration(JSONView):
    class Meta:
        model = Job
        serializer = JobSerializerResponse

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer
    parser_classes = (JSONParser, RowsCSVTextParser,)

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(request_serializer=JobFileSerializerCreateRequest,
                 response_serializer=JobSerializerResponse)
    def post(self, request, job_id, version=None):
        """
        Bulk registration of Job files (input and output filesets).

        Use `Content-Type: text/csv`, with CSV or TSV like:

        ```
        checksum,filepath,metadata,type_tags
        md5:7d9960c77b363e2c2f41b77733cf57d4,input/some_dir/table.txt,{},"text,csv,google-sheets"
        md5:d0cfb796d371b0182cd39d589b1c1ce3,input/some_dir/sample1_R2.fastq.gz,{},fastq
        md5:a97e04b6d1a0be20fcd77ba164b1206f,input/some_dir/sample2_R2.fastq.gz,{},fastq
        md5:7c9f22c433ae679f0d82b12b9a71f5d3,output/sample2/alignments/sample2.bam,{"some":"metdatas"},"bam,alignment,bam.sorted,jbrowse"
        md5:e57ea180602b69ab03605dad86166fa7,output/sample2/alignments/sample2.bai,{},"bai,jbrowse"
        ```

        File paths must begin with `input` or `output`.

        A `location` column can also be added with a URL to specify the location of files.
        You should only use this if the job stages files itself to another location
        (eg S3, Object store, ftp:// or sftp:// location).
        Otherwise Laxy handles creating the correct `location` field.

        <!--
        :param request:
        :type request:
        :param job_id:
        :type job_id:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """

        job = self.get_obj(job_id)

        if job is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        content_type = get_content_type(request)

        if content_type == 'application/json':
            serializer = JobFileSerializerCreateRequest(data=request.data,
                                                        many=True)
            if serializer.is_valid():
                # TODO: accept JSON for bulk file registration
                # separate into input and output files, add files to
                # job.input_files and job.output_files
                pass
            raise NotImplementedError()

        elif content_type == 'text/csv':
            tsv_table = request.stream.read()
            infiles, outfiles = job.add_files_from_tsv(tsv_table)

            i = FileSerializer(infiles, many=True)
            o = FileSerializer(outfiles, many=True)
            resp_data = {
                'input_files': i.data,
                'output_files': o.data
            }

            return Response(resp_data, status=status.HTTP_200_OK)


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

        content_type = get_content_type(request)
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
    def post(self, request: Request, version=None):
        """
        Create a new SampleSet. UUIDs are autoassigned.

        `samples` is an object keyed by sample name, with a list of files
        grouped by 'merge group' and pair (a 'merge group' could be a set of
        equivalent lanes the sample was split across, or a technical replicate):

        Equivalent samples (technical replicates) in different lanes can be merged -
        they could also be thought of as split FASTQ files.

        Several content-types are supported:

          - `application/json` (accepting JSON objects below)
          - `text/csv` where the POST body is CSV text as in:
             https://tools.ietf.org/html/rfc4180
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
        Repeated sample names represent 'merge groups' (eg additional lanes
        containing technical replicates).

        JSON request body example:

        A single 'sampleName' actually corresponds to a
        Sample+Condition+BiologicalReplicate.

        For two samples (R1, R2 paired end) split across two lanes, using
        File UUIDs:

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
        sample_name = request.data.get('name', 'CSV uploaded on %s' %
                                       datetime.isoformat(datetime.now()))
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

        The main purpose of this endpoint is to update job `status` and
        `exit_code`. Setting `exit_code` automatically updates the job status
        (zero implies 'complete', non-zero is 'failed').

        Note that in some cases updating job `status` may have side-effects
        beyond simply updating the Job record.
        Eg, changing `status` to "complete", "cancelled" or "failed" may
        terminate the associated compute instance if it was a single-job
        disposable ComputeResource, or trigger movement or cleanup of
        staged / temporary / intermediate files.

        Valid job statuses are:

          * "created"
          * "hold"
          * "starting"
          * "running"
          * "failed"
          * "cancelled"
          * "complete"

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

        original_status = job.status

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
            new_status = job.status

            if (new_status != original_status and
                    (new_status == Job.STATUS_COMPLETE or
                     new_status == Job.STATUS_FAILED)):
                task_data = dict(job_id=job_id)
                result = tasks.index_remote_files.apply_async(
                    args=(task_data,))
                # link_error=self._task_err_handler.s(job_id))

            if (job.done and
                    job.compute_resource and
                    job.compute_resource.disposable and
                    not job.compute_resource.running_jobs()):
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
            job = Job.objects.get(id=job_id)

            callback_url = request.build_absolute_uri(
                reverse('laxy_backend:job', args=[job.id]))

            job_event_url = request.build_absolute_uri(
                reverse('laxy_backend:create_job_eventlog', args=[job.id]))

            job_file_bulk_url = request.build_absolute_uri(reverse(
                'laxy_backend:job_file_bulk', args=[job_id]))

            # port = request.META.get('SERVER_PORT', 8001)
            # # domain = get_current_site(request).domain
            # # public_ip = requests.get('https://api.ipify.org').text
            # callback_url = (u'{scheme}://{domain}:{port}/api/v1/job/{job_id}/'.format(
            #     scheme=request.scheme,
            #     domain=PUBLIC_IP,
            #     port=port,
            #     job_id=job_id))

            # DRF API key
            # token, _ = Token.objects.get_or_create(user=request.user)
            # callback_auth_header = 'Authorization: Token %s' % token.key

            # JWT access token for user (expiring by default, so better)
            callback_auth_header = get_jwt_user_header_str(
                request.user.username)

            # TODO: Maybe use the mappings in templates/genomes.json
            #       Maybe do all genome_id to path resolution in run_job.sh
            # reference_genome_id = "Saccharomyces_cerevisiae/Ensembl/R64-1-1"
            reference_genome_id = job.params.get('params').get('genome')
            # TODO: This ID check should probably move into the PipelineRun
            #       params serializer.
            if reference_genome_id not in REFERENCE_GENOME_MAPPINGS:
                job.status = Job.STATUS_FAILED
                job.save()
                # job.delete()
                return HttpResponse(reason='Unknown reference genome',
                                    status=status.HTTP_400_BAD_REQUEST)

            task_data = dict(job_id=job_id,
                             clobber=False,
                             # this is job.params
                             # pipeline_run_config=pipeline_run.to_json(),
                             # gateway=settings.CLUSTER_MANAGEMENT_HOST,

                             # We don't pass JOB_AUTH_HEADER as 'environment'
                             # since we don't want it to leak into the shell env
                             # or any output of the run_job.sh script.
                             job_auth_header=callback_auth_header,

                             environment={
                                 'DEBUG': sh_bool(
                                     getattr(settings, 'DEBUG', False)),
                                 'JOB_ID': job_id,
                                 'JOB_COMPLETE_CALLBACK_URL':
                                     callback_url,
                                 'JOB_EVENT_URL': job_event_url,
                                 'JOB_FILE_REGISTRATION_URL': job_file_bulk_url,
                                 'JOB_INPUT_STAGED': sh_bool(False),
                                 'REFERENCE_GENOME': reference_genome_id,
                                 'PIPELINE_VERSION': '1.5.1+c53adf6',  # '1.5.1',
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
            # serializer.validated_data.update(id=job_id)

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
            serializer.validated_data.update(id=job_id)

            return Response(serializer.validated_data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 100


# TODO: When we have proper permissions, use viewsets.GenericViewSet or
# viewsets.ModelViewSet or ListAPIView instead with the appropriate permission_classes
# http://www.django-rest-framework.org/api-guide/viewsets/#modelviewset
class JobListView(generics.ListAPIView):
    """
    Retrieve a list of job for the current user.
    """

    serializer_class = JobListSerializerResponse
    # permission_classes = [IsAuthenticated]
    pagination_class = JobPagination

    def get_queryset(self):
        return (Job.objects
                .filter(owner=self.request.user)
                # .order_by('status')
                .order_by('-created_time'))

    # def list(self, request):
    #     # queryset = Job.objects.filter(owner=request.user).order_by('-created_time')
    #     queryset = self.get_queryset()
    #     serializer = JobSerializerResponse(queryset, many=True)
    #     self.transform_output(serializer.data)
    #     return Response(serializer.data)


class EventLogListView(generics.ListAPIView):
    """
    To list all events for a particular job, use:

    `/api/v1/eventlogs/?object_id={job_id}`
    """
    lookup_field = 'id'
    queryset = EventLog.objects.all()
    serializer_class = EventLogSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('user', 'object_id', 'event',)

    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (EventLog.objects
                .filter(user=self.request.user)
                .order_by('-timestamp'))


class EventLogCreate(JSONView):
    class Meta:
        model = EventLog
        serializer = EventLogSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    def post(self, request: Request, version=None, subject_obj=None):
        """
        Create a new EventLog.

        <!--
        :param subject_obj: An optional Django model that is the 'subject' of
                            the event, assigned to EventLog.obj. Mostly used for
                            subclasses that deal with events for specific
                            Model types (eg Jobs).
        :type subject_obj: django.db.models.Model
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        serializer = self.Meta.serializer(data=request.data,
                                          context={'request': request})
        if serializer.is_valid():
            if subject_obj is not None:
                event_obj = serializer.save(user=request.user,
                                            obj=subject_obj)
            else:
                event_obj = serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobEventLogCreate(EventLogCreate):
    class Meta:
        model = EventLog
        serializer = JobEventLogSerializer

    serializer_class = Meta.serializer

    def post(self, request: Request, job_id=None, version=None):
        """
        Create a new EventLog for the Job.

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        job = None
        if job_id is not None:
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        return super(JobEventLogCreate, self).post(request,
                                                   version=version,
                                                   subject_obj=job)


@api_view(['GET'])  # TODO: This should really be POST
@renderer_classes([JSONRenderer])
@permission_classes([IsAdminUser])
def trigger_file_registration(request, job_id, version=None):
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return HttpResponse(status=404, reason=f"Job {job_id} doesn't exist.")

    task_data = dict(job_id=job_id)
    result = tasks.index_remote_files.apply_async(
        args=(task_data,))
    return Response(data={'task_id': result.id},
                    content_type='application/json',
                    status=200)


class SendFileToDegust(JSONView):
    class Meta:
        model = File
        serializer = FileSerializer

    queryset = Meta.model.objects.all()
    serializer_class = Meta.serializer

    # permission_classes = (DjangoObjectPermissions,)

    # Non-async version
    # @view_config(response_serializer=RedirectResponseSerializer)
    # def post(self, request: Request, file_id: str, version=None):
    #
    #     counts_file: File = self.get_obj(file_id)
    #
    #     if not counts_file:
    #         return HttpResponse(status=status.HTTP_404_NOT_FOUND,
    #                             reason="File ID does not exist, (or your are not"
    #                                    "authorized to access it).")
    #
    #     url = 'http://degust.erc.monash.edu/upload'
    #
    #     browser = RoboBrowser(history=True, parser='lxml')
    #     browser.open(url)
    #
    #     form = browser.get_form()
    #
    #     # filelike = BytesIO(counts_file.file.read())
    #
    #     form['filename'].value = counts_file.file  # filelike
    #     browser.submit_form(form)
    #     degust_url = browser.url
    #
    #     counts_file.metadata['degust_url'] = degust_url
    #     counts_file.save()
    # #
    #     data = RedirectResponseSerializer(data={
    #         'status': browser.response.status_code,
    #         'redirect': degust_url})
    #     if data.is_valid():
    #         return Response(data=data.validated_data,
    #                         status=status.HTTP_200_OK)
    #     else:
    #         return HttpResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                             reason="Error contacting Degust.")

    @view_config(response_serializer=RedirectResponseSerializer)
    def post(self, request: Request, file_id: str, version=None):
        counts_file: File = self.get_obj(file_id)

        if not counts_file:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND,
                                reason="File ID does not exist, (or your are not"
                                       "authorized to access it).")

        saved_degust_url = counts_file.metadata.get('degust_url', None)
        if saved_degust_url:
            data = RedirectResponseSerializer(data={
                'status': status.HTTP_200_OK,
                'redirect': saved_degust_url})
            if data.is_valid():
                return Response(data=data.validated_data,
                                status=status.HTTP_200_OK)

        url = 'http://degust.erc.monash.edu/upload'
        browser = RoboBrowser(history=True, parser='lxml')
        loop = asyncio.new_event_loop()

        # This does the fetch of the form and the counts file simultaneously
        async def get_form_and_file(url, fileish):
            def get_upload_form(url):
                browser.open(url)
                return browser.get_form()

            def get_counts_file_content(fh):
                # filelike = BytesIO(fh.read())
                # return filelike
                return fh

            future_form = loop.run_in_executor(None,
                                               get_upload_form,
                                               url)
            future_file = loop.run_in_executor(None,
                                               get_counts_file_content,
                                               fileish)
            form = await future_form
            filelike = await future_file

            return form, filelike

        form, filelike = loop.run_until_complete(
            get_form_and_file(url, counts_file.file))
        loop.close()

        form['filename'].value = filelike
        browser.submit_form(form)
        degust_url = browser.url

        counts_file.metadata['degust_url'] = degust_url
        counts_file.save()

        data = RedirectResponseSerializer(data={
            'status': browser.response.status_code,
            'redirect': degust_url})
        if data.is_valid():
            return Response(data=data.validated_data,
                            status=status.HTTP_200_OK)
        else:
            return HttpResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                reason="Error contacting Degust.")


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
