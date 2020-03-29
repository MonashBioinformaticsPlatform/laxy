import asyncio
import sys
from collections import OrderedDict

import json
import shlex

import backoff
import coreapi
import coreschema
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.functional import cached_property
from django.shortcuts import redirect
from fnmatch import fnmatch
import logging
import os
import pydash

from paramiko import (SSHClient,
                      ssh_exception,
                      RSAKey,
                      AutoAddPolicy)

from laxy_backend.scraping import render_page, parse_cloudstor_links, parse_simple_index_links, is_apache_index_page, \
    parse_cloudstor_webdav
from . import paramiko_monkeypatch

from toolz import merge as merge_dicts
import requests
import rest_framework_jwt
import celery
from celery import shared_task
from datetime import datetime
from django.conf import settings
from django.contrib.admin.views.decorators import user_passes_test
from django.db import transaction
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse, FileResponse
from django.urls import reverse
from django.utils.encoding import force_text
from django_filters.rest_framework import DjangoFilterBackend, OrderingFilter
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from fs.errors import DirectoryExpected
from io import BufferedReader, BytesIO, StringIO
from pathlib import Path
import paramiko
from requests import HTTPError
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
from rest_framework.renderers import JSONRenderer, BaseRenderer, TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import Dict, List, Union
import urllib
from urllib.parse import urlparse, parse_qs
from wsgiref.util import FileWrapper

from drf_openapi.utils import view_config

from laxy_backend.storage.http_remote import is_archive_link, _check_content_size_and_resolve_redirects
from .permissions import (HasReadonlyObjectAccessToken,
                          IsOwner,
                          IsSuperuser,
                          is_owner,
                          HasAccessTokenForEventLogSubject,
                          token_is_valid,
                          FileSetHasAccessTokenForJob,
                          FileHasAccessTokenForJob)
from . import bcbio
from . import ena
from .tasks.job import (start_job,
                        index_remote_files,
                        _index_remote_files_task_err_handler,
                        set_job_status,
                        kill_remote_job,
                        estimate_job_tarball_size)

from .jwt_helpers import (get_jwt_user_header_dict,
                          get_jwt_user_header_str)
from .models import (Job,
                     ComputeResource,
                     File,
                     FileSet,
                     SampleCart,
                     PipelineRun,
                     EventLog,
                     AccessToken, get_primary_compute_location_for_files, job_path_on_compute)
from .serializers import (PatchSerializerResponse,
                          PutSerializerResponse,
                          JobSerializerResponse,
                          JobSerializerRequest,
                          ComputeResourceSerializer,
                          FileSerializer,
                          FileSerializerPostRequest,
                          FileSetSerializer,
                          FileSetSerializerPostRequest,
                          SampleCartSerializer,
                          PipelineRunSerializer,
                          PipelineRunCreateSerializer,
                          SchemalessJsonResponseSerializer,
                          JobListSerializerResponse,
                          EventLogSerializer,
                          JobEventLogSerializer,
                          JobFileSerializerCreateRequest,
                          InputOutputFilesResponse,
                          RedirectResponseSerializer,
                          FileListing,
                          AccessTokenSerializer, JobAccessTokenRequestSerializer, JobAccessTokenResponseSerializer,
                          PingResponseSerializer)
from .util import (sh_bool,
                   laxy_sftp_url,
                   generate_uuid,
                   multikeysort,
                   get_content_type)
from .storage import http_remote
from .view_mixins import (JSONView, GetMixin, PatchMixin,
                          DeleteMixin, PostMixin, CSVTextParser,
                          PutMixin, RowsCSVTextParser, etag_headers, JSONPatchMixin)

# from .models import User
from django.contrib.auth import get_user_model

from .data.genomics.genomes import REFERENCE_GENOME_MAPPINGS
from contextlib import closing

# This is a mapping of 'matchers' to link parsing functions.
# The matchers can be simple strings, which are tested as a substring of the URL,
# or a function like matcher(url, page_text). The matcher function returns True or False.
LINK_SCRAPER_MAPPINGS = [
    ('://cloudstor.aarnet.edu.au/plus/s/', parse_cloudstor_webdav),
    # ('://cloudstor.aarnet.edu.au/plus/s/', parse_cloudstor_links),
    (is_apache_index_page, parse_simple_index_links),
    ('://', parse_simple_index_links),
]

User = get_user_model()

logger = logging.getLogger(__name__)


class PingView(APIView):
    renderer_classes = (JSONRenderer,)
    permission_classes = (AllowAny,)

    @view_config(response_serializer=PingResponseSerializer)
    def get(self, request, version=None):
        """
        Used by clients to poll if the backend is online.
        """
        app_version = getattr(settings, 'VERSION', 'unspecified')
        env = getattr(settings, 'ENV', 'unspecified')
        return JsonResponse(PingResponseSerializer({'version': app_version,
                                                    'env': env,
                                                    'status': 'online'}).data)


class JobDirectTarDownload(JSONView):
    lookup_url_kwarg = 'job_id'
    queryset = Job.objects.all()
    permission_classes = (IsOwner | IsSuperuser | HasReadonlyObjectAccessToken,)

    def get(self, request, job_id, version=None):
        """
        Download a tar.gz of every file in the job.

        Supports `?access_token=` query parameter for obfuscated public link sharing.
        """

        # must get object this way to correctly enforce permission_classes !
        job = self.get_object()

        # NOTE: The download method used here will only
        # work on a job stored in a single SSH-accessible location, not one with
        # archived files spread across object store etc. The MyTardis-style tarball
        # download, using django-storages, would be required to do tarball downloads
        # in that case.
        # job_path = job.abs_path_on_compute
        stored_at = get_primary_compute_location_for_files(job.get_files())
        job_path = job_path_on_compute(job, stored_at)

        client = stored_at.ssh_client()
        stdin, stdout, stderr = client.exec_command(f'tar -chzf - --directory "{job_path}" .')

        if request.path.endswith('.tar.gz'):
            output_fn = f'{job.id}.tar.gz'
        else:
            output_fn = f'laxy_job_{job.id}.tar.gz'
        return FileResponse(stdout, filename=output_fn, as_attachment=True)


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

    @backoff.on_exception(backoff.expo,
                          (EOFError,
                           IOError,
                           OSError,
                           ssh_exception.SSHException,
                           ssh_exception.AuthenticationException,
                           ),
                          max_tries=3,
                          jitter=backoff.full_jitter)
    def render(self, filelike,
               media_type=None,
               renderer_context=None,
               blksize=8192):
        iterable = FileWrapper(filelike, blksize=blksize)
        try:
            for chunk in iterable:
                yield chunk
        except ssh_exception.SSHException as ex:
            raise IOError(str(ex) + '(paramiko.ssh_exception.SSHException)').with_traceback(sys.exc_info()[2])
        except OSError as ex:
            raise IOError(str(ex) + '(OSError)').with_traceback(sys.exc_info()[2])


class RemoteFilesQueryParams(QueryParamFilterBackend):
    def __init__(self):
        super().__init__([
            dict(name='url',
                 example='https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data/',
                 description='A URL containing links to input data files'),
            dict(name='fileglob',
                 example='*.fastq.gz',
                 description="A glob (wildcard) expression to filter files returned. Doesn't filter directories"),
        ])


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


class ENASpeciesLookupView(APIView):
    renderer_classes = (JSONRenderer,)
    serializer_class = SchemalessJsonResponseSerializer
    api_docs_visible_to = 'public'

    # permission_classes = (AllowAny,)

    @view_config(response_serializer=SchemalessJsonResponseSerializer)
    def get(self, request, accession: str, version=None):
        """
        Queries ENA with a sample accession and returns the species information.

        Response example:
        ```json
         {
          "taxon_id":"10090",
          "scientific_name":"Mus musculus",
          "common_name":"house mouse"
         }
        ```

        <!--
        :param accession: An ENA sample accession (eg SAMN07548382)
        :type accession: str
        :param request:
        :type request:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """

        try:
            ena_result = ena.get_organism_from_sample_accession(accession)
            return Response(ena_result, status=status.HTTP_200_OK)
        except IndexError as ex:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        except HTTPError as ex:
            raise ex


class FileCreate(JSONView):
    queryset = File.objects.all()
    serializer_class = FileSerializer

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

        serializer = self.get_serializer(data=request.data)
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
        if obj_ref is None:
            return None
        if isinstance(obj_ref, str):
            try:
                obj = File.objects.get(id=obj_ref)
            except File.DoesNotExist:
                return None
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

    @backoff.on_exception(backoff.expo,
                          (EOFError,
                           IOError,
                           OSError,
                           ssh_exception.SSHException,
                           ssh_exception.AuthenticationException,
                           ),
                          max_tries=3,
                          jitter=backoff.full_jitter)
    def _stream_response(
            self,
            obj_ref: Union[str, File],
            filename: str = None,
            download: bool = True) -> Union[StreamingHttpResponse, Response]:

        obj = self._as_file_obj(obj_ref)

        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        renderer = StreamingFileDownloadRenderer()
        # TODO: For local file:// URLs, django.http.response.FileResponse will probably preform better
        response = StreamingHttpResponse(
            renderer.render(obj.file),
            content_type=renderer.media_type)

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
        return self._stream_response(obj_ref, filename, download=True)

    def view(self, obj_ref: Union[str, File], filename=None):
        return self._stream_response(obj_ref, filename, download=False)


class FileContentDownload(StreamFileMixin,
                          GetMixin,
                          JSONView):
    queryset = File.objects.all()
    serializer_class = FileSerializer

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
               JSONPatchMixin,
               JSONView):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    parser_classes = (JSONParser,
                      JSONPatchRFC7386Parser,
                      JSONPatchRFC6902Parser)

    permission_classes = (IsOwner | IsSuperuser | HasReadonlyObjectAccessToken,)

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=FileSerializer)
    @etag_headers
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
            except (ssh_exception.AuthenticationException,
                    ssh_exception.SSHException,
                    EOFError) as ex:
                return HttpResponse(
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    reason="Error accessing file via SFTP storage backend")

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

        for field in File.ExtraMeta.patchable_fields:
            resp = self._try_json_patch(request, field=field)

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
    queryset = Job.objects.all()
    serializer_class = FileSerializer
    parser_classes = (JSONParser,)

    permission_classes = (IsOwner | IsSuperuser | HasReadonlyObjectAccessToken,)

    @view_config(response_serializer=FileSerializer)
    @etag_headers
    def get(self,
            request: Request,
            uuid: str,
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
        :param uuid:
        :type uuid:
        :param file_path:
        :type file_path:
        :return:
        :rtype:
        -->
        """

        job = self.get_object()
        if job is None:
            return Response({'detail': f'Unknown job ID: {uuid}'},
                            status=status.HTTP_404_NOT_FOUND)

        fname = Path(file_path).name
        fpath = Path(file_path).parent
        file_obj = job.get_files().filter(name=fname, path=fpath).first()
        if file_obj is None:
            return Response({'detail': f'Cannot find file in job {uuid} by path/filename'},
                            status=status.HTTP_404_NOT_FOUND)

        # serializer = self.get_serializer(instance=file_obj)
        # return Response(serializer.data, status=status.HTTP_200_OK)

        content_type = get_content_type(request)
        if content_type == 'application/json':
            return super().get(request, file_obj.id)
        else:
            try:
                # File view/download is the default when no Content-Type is specified
                if 'download' in request.query_params:
                    logger.debug(f"Attempting download of {file_obj.id}")
                    return super().download(file_obj, filename=fname)
                else:
                    logger.debug(f"Attempting view in browser of {file_obj.id}")
                    return super().view(file_obj, filename=fname)
            except (ssh_exception.AuthenticationException,
                    ssh_exception.SSHException,
                    EOFError) as ex:
                return HttpResponse(
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    reason="Error accessing file via SFTP storage backend")

        # return super(FileView, self).get(request, file_obj.id)

    @transaction.atomic()
    @view_config(request_serializer=JobFileSerializerCreateRequest,
                 response_serializer=FileSerializer)
    def put(self,
            request: Request,
            uuid: str,
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
        :param uuid:
        :type uuid:
        :param file_path:
        :type file_path:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """
        job = self.get_object()
        fname = Path(file_path).name
        fpath = Path(file_path).parent

        fileset_path = fpath.parts[0]

        if fileset_path == 'output':
            fileset = job.output_files
        elif fileset_path == 'input':
            fileset = job.input_files
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Generate a File.location URL if not set explicitly
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
                fileset.add(serializer.instance)
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


# TODO: This endpoint should properly set owner, location etc
class JobFileBulkRegistration(JSONView):
    queryset = Job.objects.all()
    serializer_class = JobSerializerResponse
    parser_classes = (JSONParser, RowsCSVTextParser,)

    permission_classes = (IsOwner | IsSuperuser,)

    @view_config(request_serializer=JobFileSerializerCreateRequest,
                 response_serializer=JobSerializerResponse)
    def post(self, request, uuid, version=None):
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
        :param uuid:
        :type uuid:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """

        job = self.get_object()

        content_type = get_content_type(request)
        if content_type == 'application/json':
            serializer = self.request_serializer(data=request.data, many=True)
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
    queryset = FileSet.objects.all()
    serializer_class = FileSetSerializer

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
    queryset = FileSet.objects.all()
    serializer_class = FileSetSerializer

    permission_classes = (IsAuthenticated | FileSetHasAccessTokenForJob,)

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=FileSetSerializer)
    @etag_headers
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


class SampleCartCreateUpdate(JSONView):
    queryset = SampleCart.objects.all()
    serializer_class = SampleCartSerializer
    parser_classes = (JSONParser, MultiPartParser, CSVTextParser,)

    def create_update(self, request, obj):
        """
        Replaces an existing SampleCart with new content, or creates a new one if `uuid` is None.

        :param obj:
        :type obj:
        :param request:
        :type request:
        :return:
        :rtype:
        """

        if not obj.name:
            obj.name = 'Sample set created on %s' % datetime.isoformat(datetime.now())

        content_type = get_content_type(request)
        encoding = 'utf-8'

        if content_type == 'multipart/form-data':
            if not obj.name:
                obj.name = 'CSV uploaded on %s' % datetime.isoformat(datetime.now())
            fh = request.data.get('file', None)
            csv_table = fh.read().decode(encoding)
            obj.from_csv(csv_table)

            return Response(self.get_serializer(instance=obj).data, status=status.HTTP_200_OK)

        elif content_type == 'text/csv':
            if not obj.name:
                obj.name = 'CSV uploaded on %s' % datetime.isoformat(datetime.now())
            csv_table = request.data
            obj.from_csv(csv_table)

            return Response(self.get_serializer(instance=obj).data, status=status.HTTP_200_OK)

        elif content_type == 'application/json':
            serializer = self.get_serializer(instance=obj, data=request.data)
            if serializer.is_valid():
                obj = serializer.save(owner=request.user)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(None, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)


class SampleCartCreate(SampleCartCreateUpdate):

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(request_serializer=SampleCartSerializer,
                 response_serializer=SampleCartSerializer)
    def post(self, request: Request, version=None):
        """
        Create a new SampleCart. UUIDs are autoassigned.

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

        *TODO*: Change this to files: [{R1: {location: "http://foo/bla.txt", name: "bla.txt}] form
        shaped like a subset of models.File fields.

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

        samplecart_name = request.data.get('name', None)
        obj = SampleCart(name=samplecart_name, owner=request.user)
        return self.create_update(request, obj)


class SampleCartView(GetMixin,
                     DeleteMixin,
                     SampleCartCreateUpdate):

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=SampleCartSerializer)
    @etag_headers
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
        return super(SampleCartView, self).get(request, uuid)

    @view_config(request_serializer=SampleCartSerializer,
                 response_serializer=PutSerializerResponse)
    def put(self, request, uuid, version=None):
        obj = self.get_object()
        if 'id' in request.data:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="id cannot be updated")

        sample_name = request.data.get('name', None)
        if sample_name is not None:
            obj.name = sample_name

        return self.create_update(request, obj)

    # TODO: CSV upload doesn't append/merge, it aways creates a new SampleCart.
    #       Implement PATCH method so we can append/merge an uploaded CSV rather
    #       than just replace wholesale
    #
    # @view_config(request_serializer=SampleCartSerializer,
    #              response_serializer=PatchSerializerResponse)
    # def patch(self, request, uuid, version=None):
    #     return super(SampleCartView, self).patch(request, uuid)


class ComputeResourceView(GetMixin,
                          DeleteMixin,
                          JSONView):
    queryset = ComputeResource.objects.all()
    serializer_class = ComputeResourceSerializer
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
        obj = self.get_object()

        serializer = self.get_serializer(instance=obj, data=request.data, partial=True)
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
    queryset = ComputeResource.objects.all()
    serializer_class = ComputeResourceSerializer
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
          * `queue_type` - `slurm` or `local` - determines to do job submission,
             monitoring and cancellation for this host. This is passed to the job
             script (eg `run_job.sh`), to tell it to either submit long-running
             tasks to a SLURM queue (via sbatch/srun), or run all processes on the
             local compute node.
          * `slurm_account` (optional) - the SLURM account name to use
             (eg for the `sbatch --account=` option).

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
    queryset = PipelineRun.objects.all()
    serializer_class = PipelineRunCreateSerializer

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
    queryset = PipelineRun.objects.all()
    serializer_class = PipelineRunSerializer

    # permission_classes = (DjangoObjectPermissions,)

    @view_config(response_serializer=PipelineRunSerializer)
    @etag_headers
    def get(self, request: Request, uuid, version=None):
        """
        Returns info about a PipelineRun, specified by UUID.

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
        :param uuid: The PipelineRun id to update.
        :type uuid: str
        :param version:
        :type version:
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        return super(PipelineRunView, self).put(
            request,
            uuid,
            serializer_class=PipelineRunCreateSerializer)


class JobView(JSONPatchMixin,
              JSONView):
    queryset = Job.objects.all()
    serializer_class = JobSerializerResponse

    permission_classes = (IsOwner | IsSuperuser | HasReadonlyObjectAccessToken,)
    # permission_classes = (DjangoObjectPermissions,)

    parser_classes = (JSONParser,
                      JSONPatchRFC7386Parser,
                      JSONPatchRFC6902Parser)

    @view_config(response_serializer=JobSerializerResponse)
    @etag_headers
    def get(self, request: Request, uuid, version=None):
        """
        Returns info about a Job, specified by Job ID (UUID).

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @view_config(request_serializer=JobSerializerRequest,
                 response_serializer=PatchSerializerResponse)
    def patch(self, request: Request, uuid, version=None):
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

        Also supports json patching for params and metadata if the `Content-Type`
        is `application/merge-patch+json` or `application/json-patch+json`.

        <!--
        :param request:
        :type request: rest_framework.request.Request
        :param uuid: The Job id.
        :type uuid: str
        :return:
        :rtype: rest_framework.response.Response
        -->
        """
        job = self.get_object()
        original_status = job.status

        patchable_fields = Job.ExtraMeta.patchable_fields
        if self._is_json_patch_content_type(request):
            for field in patchable_fields:
                request = self._patch_request(request, obj=job, field=field)
        else:
            if any([request.data.get(field, None) for field in patchable_fields]):
                return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                    reason=f"Invalid Content-Type for PATCH on: {', '.join(patchable_fields)}. "
                                           f"Use application/merge-patch+json or application/json-patch+json")

        serializer = self.get_serializer(instance=job,
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

            if job_status == Job.STATUS_CANCELLED:
                kill_remote_job.apply_async(args=(dict(job_id=uuid),))

            new_status = serializer.validated_data.get('status')

            if (new_status != original_status and
                    (new_status == Job.STATUS_COMPLETE or
                     new_status == Job.STATUS_FAILED)):

                # We don't update the status yet - an async task will do this after file indexing is complete
                serializer.save(status=original_status)
                # job = Job.objects.get(id=uuid)

                task_data = dict(job_id=uuid, status=new_status)
                # result = =index_remote_files.apply_async(
                #     args=(task_data,))
                # link_error=self._task_err_handler.s(job_id))
                result = celery.chain(index_remote_files.s(task_data),
                                      set_job_status.s()).apply_async(
                    link_error=_index_remote_files_task_err_handler.s(job_id=job.id))

                # We fire this off but aren't too concerned if it fails
                estimate_job_tarball_size.s(task_data).apply_async()

            else:
                serializer.save()
                # job = Job.objects.get(id=uuid)

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request: Request, uuid, version=None):
        """

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: A job UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        job = self.get_object()
        if job.compute_resource.disposable:
            task_data = dict(job_id=uuid)
            job.compute_resource.dispose()

        job.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


def get_abs_backend_url(path_query_frag: str, request: Union[None, Request] = None) -> str:
    """
    Given a path?query=string#and_fragment (eg produced by the django 'reverse' function).
    return the absolute URL to the API backend.

    Optionally, a request object can be provided to help guess the scheme, FQDN or hostname and port.

    If the FRONTEND_API_URL setting (LAXY_FRONTEND_API_URL environment variable) is defined,
    this is used as the hostname:port. If no scheme is specified in FRONTEND_API_URL, the
    USE_SSL setting determines the scheme.

    :param path_query_frag:
    :type path_query_frag:
    :param request:
    :type request:
    :return:
    :rtype:
    """
    # return urlparse(''.join(settings.LAXY_FRONTEND_API_URL, path_query_frag)).geturl()

    api_baseurl = settings.FRONTEND_API_URL
    if request is None and not api_baseurl:
        raise ValueError('LAXY_FRONTEND_API_URL is not set; a request arg must be provided.')

    if request is not None:
        url = urlparse(request.build_absolute_uri(path_query_frag))
    if api_baseurl:
        apiurl = urlparse(api_baseurl)
        url = url._replace(netloc=apiurl.netloc)
        if apiurl.scheme:
            url = url._replace(scheme=apiurl.scheme)
    if not url.scheme:
        url = url._replace(scheme='https' if settings.USE_SSL else 'http')

    return url.geturl()


class JobCreate(JSONView):
    queryset = Job.objects.all()
    serializer_class = JobSerializerRequest

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

        pipeline_run_id = request.query_params.get('pipeline_run_id', None)
        samplecart_id = None
        if pipeline_run_id:
            try:
                pipelinerun_obj = PipelineRun.objects.get(id=pipeline_run_id)
                pipelinerun = PipelineRunSerializer(pipelinerun_obj).data
                samplecart_id = pipelinerun.get('sample_cart', {}).get('id', None)
                pipelinerun['pipelinerun_id'] = str(pipelinerun['id'])
                del pipelinerun['id']
                request.data['params'] = json.dumps(pipelinerun)

            except PipelineRun.DoesNotExist:
                return HttpResponse(reason='pipeline_run %s does not exist'
                                           % pipeline_run_id,
                                    status=status.HTTP_400_BAD_REQUEST)

        serializer = self.request_serializer(data=request.data,
                                             context={'request': request})

        if serializer.is_valid():

            job_status = serializer.validated_data.get('status', '')
            if job_status != '' and job_status != Job.STATUS_HOLD:
                return HttpResponse(reason='status can only be set to "%s" '
                                           'or left unset for job creation'
                                           % Job.STATUS_HOLD,
                                    status=status.HTTP_400_BAD_REQUEST)

            job = serializer.save()  # owner=request.user)

            # We associate the previously created SampleCart with our new Job object
            # (SampleCarts effectively should be readonly once associated with a Job).
            if samplecart_id:
                samplecart = SampleCart.objects.get(id=samplecart_id)
                samplecart.job = job
                samplecart.save()

            if not job.compute_resource:
                default_compute = _get_default_compute_resource(job)
                job.compute_resource = default_compute
                job.save()

            if job.status == Job.STATUS_HOLD:
                return Response(serializer.data, status=status.HTTP_200_OK)

            job_id = job.id
            job = Job.objects.get(id=job_id)

            callback_url = get_abs_backend_url(
                reverse('laxy_backend:job', args=[job.id]),
                request)

            job_event_url = get_abs_backend_url(
                reverse('laxy_backend:create_job_eventlog', args=[job.id]),
                request)

            job_file_bulk_url = get_abs_backend_url(
                reverse('laxy_backend:job_file_bulk', args=[job_id]),
                request)

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
            callback_auth_header = get_jwt_user_header_str(request.user.username)

            # TODO: Maybe use the mappings in templates/genomes.json
            #       Maybe do all genome_id to path resolution in run_job.sh
            # reference_genome_id = "Saccharomyces_cerevisiae/Ensembl/R64-1-1"
            reference_genome_id = job.params.get('params').get('genome')

            # TODO: Validate that pipeline_version and pipeline_aligner are
            #       one of the valid values, as per reference_genome_id
            #       We really need a consistent way / pattern to do this server-side 'form validation'
            #       maybe with a DRF Serializer.
            #       (probably the frontend should request valid values from the backend to populate forms,
            #        and then use the same data to validate serverside, as per REFERENCE_GENOME_MAPPINGS)
            default_pipeline_version = '1.5.4'  # '1.5.1+c53adf6'  # '1.5.1'
            pipeline_version = job.params.get('params').get('pipeline_version', default_pipeline_version)
            pipeline_aligner = job.params.get('params').get('pipeline_aligner', 'star')

            # TODO: This ID check should probably move into the PipelineRun
            #       params serializer.
            if reference_genome_id not in REFERENCE_GENOME_MAPPINGS:
                job.status = Job.STATUS_FAILED
                job.save()
                # job.delete()
                return HttpResponse(reason='Unknown reference genome',
                                    status=status.HTTP_400_BAD_REQUEST)

            slurm_account = job.compute_resource.extra.get('slurm_account', None)

            environment = dict(
                DEBUG=sh_bool(
                    getattr(settings, 'DEBUG', False)),
                IGNORE_SELF_SIGNED_CERTIFICATE=sh_bool(False),
                JOB_ID=job_id,
                JOB_PATH=job.abs_path_on_compute,
                JOB_COMPLETE_CALLBACK_URL=callback_url,
                JOB_EVENT_URL=job_event_url,
                JOB_FILE_REGISTRATION_URL=job_file_bulk_url,
                JOB_INPUT_STAGED=sh_bool(False),
                REFERENCE_GENOME=shlex.quote(reference_genome_id),
                PIPELINE_VERSION=shlex.quote(pipeline_version),
                PIPELINE_ALIGNER=shlex.quote(pipeline_aligner),
                QUEUE_TYPE=job.compute_resource.queue_type or 'local',
                # BDS_SINGLE_NODE=sh_bool(False),
                SLURM_ACCOUNT=slurm_account or '',
            )

            task_data = dict(job_id=job_id,
                             clobber=False,
                             # this is job.params
                             # pipeline_run_config=pipeline_run.to_json(),
                             # gateway=settings.CLUSTER_MANAGEMENT_HOST,

                             # We don't pass JOB_AUTH_HEADER as 'environment'
                             # since we don't want it to leak into the shell env
                             # or any output of the run_job.sh script.
                             job_auth_header=callback_auth_header,
                             environment=environment)

            # TESTING: Start cluster, run job, (pre-existing data), stop cluster
            # tasks.run_job_chain(task_data)

            result = start_job.apply_async(
                args=(task_data,),
                link_error=self._task_err_handler.s(job_id))
            # Non-async for testing
            # result = start_job(task_data)

            # result = celery.chain(# tasks.stage_job_config.s(task_data),
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

            serializer = self.response_serializer(job)
            return Response(serializer.data, status=status.HTTP_200_OK)

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


class BigPageNumberPagination(PageNumberPagination):
    page_size = 100
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 1000


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
    pagination_class = BigPageNumberPagination

    permission_classes = (IsAuthenticated | HasAccessTokenForEventLogSubject,)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return (EventLog.objects
                    .order_by('-timestamp'))
        else:
            # If access_token is provided in query string, check it is valid for the requested the Job (object_id)
            # and if so return Events for the Job
            token = self.request.query_params.get('access_token', None)
            obj_id = self.request.query_params.get('object_id', None)
            if token and obj_id and token_is_valid(token, obj_id):
                return (EventLog.objects
                        .filter(object_id=obj_id)
                        .order_by('-timestamp'))
            else:
                return (EventLog.objects
                        .filter(user=self.request.user)
                        .order_by('-timestamp'))


class EventLogCreate(JSONView):
    queryset = EventLog.objects.all()
    serializer_class = EventLogSerializer

    def post(self, request: Request, version=None, subject_obj=None):
        """
        Create a new EventLog.

        These logs are intended to report events, but not trigger side effects.

        Request body example:
        ```json
        {
         "event": "JOB_PIPELINE_COMPLETED",
         "message": "Job completed.",
         "extra": {"exit_code": 0},
         "content_type": "job",
         "object_id": "2w3iIE9BLKrnwHBz1xUtl9"
        }
        ```

        `event` is an 'enum' or 'tag' style string classifying the logged event - values
        aren't currently enforced, but should generally be one of:

        - `JOB_STATUS_CHANGED`
        - `INPUT_DATA_DOWNLOAD_STARTED`
        - `INPUT_DATA_DOWNLOAD_FINISHED`
        - `JOB_PIPELINE_STARTING`
        - `JOB_PIPELINE_FAILED`
        - `JOB_PIPELINE_COMPLETED`
        - `JOB_INFO`
        - `JOB_ERROR`

        `message` is a short free-text string intended to be read by humans.

        `extra` contains arbitrary metadata about the event - conventions in use
        include numeric process `exit_code`, and job status changes `from` and `to`.

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

        serializer = self.get_serializer(data=request.data,
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
    serializer_class = JobEventLogSerializer

    def post(self, request: Request, uuid=None, version=None):
        """
        Create a new EventLog for the Job.
        See <a href="#operation/v1_eventlog_create">/eventlog/</a> docs
        (`content_type` and `object_id` are automatically set to the Job {job_id}).

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """

        job = None
        if uuid is not None:
            try:
                job = Job.objects.get(id=uuid)
            except Job.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        if job.owner == request.user or request.user.is_superuser:
            return super(JobEventLogCreate, self).post(request,
                                                       version=version,
                                                       subject_obj=job)

        return Response(status=status.HTTP_403_FORBIDDEN)


class AccessTokenView(JSONView, GetMixin, DeleteMixin):
    queryset = AccessToken.objects.all()
    serializer_class = AccessTokenSerializer
    permission_classes = (IsAuthenticated & (IsOwner | IsSuperuser),)


class AccessTokenListView(generics.ListAPIView):
    """
    List access tokens sorted by expiry time.

    Query parameters:

    * active - if set, show only non-expired tokens (eg `?active=1`)
    * object_id - the ID of the object this access token gives permission to access
    * content_type - the content type (eg "job") of the target object
    * created_by - filter by user (available only to superusers)
    """

    lookup_field = 'id'
    queryset = AccessToken.objects.all()
    serializer_class = AccessTokenSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('created_by', 'content_type', 'object_id',)

    permission_classes = (IsAuthenticated & (IsOwner | IsSuperuser),)

    # FIXME: Filtering by ?content_type=job fails to return results
    def get_queryset(self):
        qs = self.queryset
        active = self.request.query_params.get('active', None)
        # qs = qs.filter(created_by=self.request.user)  # handled by permission_classes
        if active:
            qs = qs.filter(Q(expiry_time__gt=datetime.now()) | Q(expiry_time=None))

        return qs.order_by('-expiry_time')


class AccessTokenCreate(JSONView):
    queryset = AccessToken.objects.all()
    serializer_class = AccessTokenSerializer
    permission_classes = (IsAuthenticated & (IsOwner | IsSuperuser),)

    def _owns_target_object(self, user, serializer):
        content_type = serializer.validated_data.get('content_type', 'job')
        object_id = serializer.validated_data.get('object_id', None)
        target_obj = ContentType.objects.get(
            app_label='laxy_backend',
            model=content_type
        ).get_object_for_this_type(id=object_id)

        return is_owner(user, target_obj)

    def post(self, request: Request, version=None):
        """
        Generate a time-limited access token for a specific object.
        Can be used like `?access_token={the_token}` in certain URLs to provide
        read-only access.
        """
        serializer = self.get_serializer(data=request.data,
                                         context={'request': request})
        if serializer.is_valid():
            if not self._owns_target_object(request.user, serializer):
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

            obj = serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobAccessTokenView(JSONView, GetMixin):
    """
    This view can be used if we want just one token link per job which can be updated with a new expiry or deleted.
    This simplifies the use of token links for users, at the cost of less flexibility.
    """
    lookup_url_kwarg = 'job_id'
    queryset = AccessToken.objects.all()
    serializer_class = JobAccessTokenRequestSerializer
    permission_classes = (IsSuperuser, IsOwner, HasReadonlyObjectAccessToken,)

    @cached_property
    def _job_ct(self) -> ContentType:
        return ContentType.objects.get(app_label='laxy_backend', model='job')

    def _owns_target_object(self, user, obj_id):
        target_obj = ContentType.objects.get(
            app_label='laxy_backend',
            model=self._job_ct
        ).get_object_for_this_type(id=obj_id)

        return is_owner(user, target_obj) or self.request.user.is_superuser

    def get_queryset(self):
        job_id = self.kwargs.get(self.lookup_url_kwarg, None)

        if job_id is not None:
            qs = (self.queryset
                  .filter(Q(object_id=job_id) & Q(content_type=self._job_ct))
                  .order_by('created_time'))

            return qs

        return AccessToken.objects.none()

    @view_config(response_serializer=JobAccessTokenResponseSerializer)
    def get(self, request: Request, job_id: str, version=None):
        """
        Returns the (first created, non-hidden) AccessToken for this job.

        <!--
        :param request: The request object.
        :type request:
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype:
        -->
        """
        obj = self.get_queryset().first()
        if obj:
            serializer = self.response_serializer(obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)

    @view_config(request_serializer=JobAccessTokenRequestSerializer,
                 response_serializer=JobAccessTokenResponseSerializer)
    def put(self, request: Request, job_id: str, version=None):
        """
        Create or update the access token for this Job.
        This always updates the first created, non-hidden token.

        (`content_type` and `object_id` will be ignored - these are always `'job'` and the value of `job_id` at
        this endpoint).

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

        # We must check that the requesting user own the target Job, since the IsOwner permission (on the class) in
        # this context applies to the AccessToken, not the Job itself.
        # This ensures users can't create an AccessToken for a Job they don't own !
        if not self._owns_target_object(request.user, job_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        obj = self.get_queryset().first()

        if obj:
            serializer = self.request_serializer(obj, data=request.data,
                                                 context={'request': request})
        else:
            data = dict(request.data)
            data.update(object_id=job_id, content_type='job')
            serializer = self.request_serializer(data=data,
                                                 context={'request': request})

        if serializer.is_valid():
            obj = serializer.save(created_by=request.user)

            return Response(self.response_serializer(obj).data,
                            status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobClone(JSONView):
    queryset = Job.objects.all()
    serializer_class = JobSerializerResponse

    permission_classes = (IsOwner | IsSuperuser,)

    # permission_classes = (DjangoObjectPermissions,)

    lookup_url_kwarg = 'job_id'

    @view_config(response_serializer=JobSerializerResponse)
    @etag_headers
    def post(self, request: Request, job_id, version=None):
        """
        Returns info about a Job, specified by Job ID (UUID).

        <!--
        :param request: The request object.
        :type request: rest_framework.request.Request
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype: rest_framework.response.Response
        -->
        """
        job = self.get_object()

        samplecart_id = job.params.get('sample_cart', {}).get('id', None)
        # TODO: This should actually be a migration that modifies Job.params to conform to the new
        #       shape. We should probably start versioning our JSON blobs, or including a link to
        #       a JSON Schema (eg generated via marshmallow-jsonschema and linked to in the JSON blob
        #       something like {"schema": "https://laxy.io/api/v1/schemas/job.params/version-2"}).
        #       Advantage of this is we can then automatically generate TypeScript types in the
        #       frontend too using: https://www.npmjs.com/package/json-schema-to-typescript
        #
        if samplecart_id is None:
            samplecart_id = job.params.get('sample_set', {}).get('id', None)

        if samplecart_id is None:
            return HttpResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                reason=f'Cannot find samplecart associated with job {job.id}')
        pipelinerun = PipelineRun.objects.filter(sample_cart=samplecart_id).first()
        samplecart = pipelinerun.sample_cart

        samplecart.pk = None
        samplecart.id = None
        # SampleCart is being cloned in order to be used for a new Job, so unset this
        samplecart.job = None
        samplecart.save()
        new_samplecart = samplecart

        pipelinerun.pk = None
        pipelinerun.id = None
        pipelinerun.sample_cart = new_samplecart
        pipelinerun.save()
        new_pipelinerun = pipelinerun

        return JsonResponse({'pipelinerun_id': new_pipelinerun.id, 'samplecart_id': new_samplecart.id})


# TODO: This should really be POST, since it has side effects,
#       however GET is easier to trigger manually in the browser
@api_view(['GET'])
@renderer_classes([JSONRenderer])
@permission_classes([IsAdminUser])
def trigger_file_registration(request, job_id, version=None):
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return HttpResponse(status=404, reason=f"Job {job_id} doesn't exist.")

    task_data = dict(job_id=job_id)
    result = index_remote_files.apply_async(
        args=(task_data,))
    return Response(data={'task_id': result.id},
                    content_type='application/json',
                    status=200)


class SendFileToDegust(JSONView):
    lookup_url_kwarg = 'file_id'
    queryset = File.objects.all()
    serializer_class = FileSerializer

    permission_classes = (IsOwner | IsSuperuser | FileHasAccessTokenForJob,)

    # Non-async version
    # @view_config(response_serializer=RedirectResponseSerializer)
    # def post(self, request: Request, file_id: str, version=None):
    #
    #     counts_file: File = self.get_object()
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
        """
        Sends the File specified by `file_id` to the Degust web app (http://degust.erc.monash.edu).
        The file should be a compatible counts matrix (eg TSV).
        Creates a new Degust session if the file hasn't been send before, or returns the URL to the existing
        session if it has.

        Response:

        The HTTP status code returned by Degust, and if successful the URL to the Degust session.

        ```json
        {
          "status": 200
          "redirect": "http://degust.erc.monash.edu/degust/config.html?code=abfa3b7a2b726bfadcf3076f6feb3ecd"
         }
        ```
        """

        degust_api_url = getattr(settings, 'DEGUST_URL', 'http://degust.erc.monash.edu')

        counts_file: File = self.get_object()
        job = counts_file.fileset.jobs_as_output.first()
        sample_cart = job.params.get('sample_cart', {})
        samples = sample_cart.get('samples', [])
        conditions = list(set([sample['metadata'].get('condition') for sample in samples]))
        # {'some_condition': []} dict of empty lists
        degust_conditions = OrderedDict([(condition, []) for condition in conditions])

        for sample in samples:
            name = sample['name']
            condition = sample['metadata'].get('condition')
            degust_conditions[condition].append(name)

        if not counts_file:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND,
                                reason="File ID does not exist, (or your are not"
                                       "authorized to access it).")

        saved_degust_url = counts_file.metadata.get('degust_url', None)
        # force_new is mostly for testing, creates a new Degust session overwriting the cached URL in File metadata
        force_new = request.query_params.get('force_new', False)
        if saved_degust_url and not force_new:
            data = RedirectResponseSerializer(data={
                'status': status.HTTP_200_OK,
                'redirect': saved_degust_url})
            if data.is_valid():
                return Response(data=data.validated_data,
                                status=status.HTTP_200_OK)

        # TODO: RoboBrowser is still required since while Degust no longer requires a CSRF token upon upload,
        #       an 'upload_token' per-user is required:
        #       https://github.com/drpowell/degust/blob/master/FAQ.md#uploading-a-counts-file-from-the-command-line
        #       We either need an application level API token for Degust (to create anonymous uploads), or a
        #       trust relationship (eg proper OAuth2 provider or simple shared Google Account ID) that allows
        #       Laxy to retrieve the upload token for a user programmatically
        url = f'{degust_api_url}/upload'
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

        # First POST the counts file, get a new Degust session ID
        form['filename'].value = filelike

        # TODO: This is to deal with SFTPStorage backend timeouts etc
        #       Ideally we would fork / subclass SFTPStorage and SFTPStorageFile
        #       and add some built-in backoff / retry functionality
        #       eg: https://github.com/MonashBioinformaticsPlatform/laxy/issues/52
        @backoff.on_exception(backoff.expo,
                              (EOFError,
                               IOError,
                               OSError,
                               ssh_exception.SSHException,
                               ssh_exception.AuthenticationException,
                               ),
                              max_tries=3,
                              jitter=backoff.full_jitter)
        def submit_form(form):
            browser.submit_form(form)

        submit_form(form)

        degust_config_url = browser.url.replace('/compare.html?', '/config.html?', 1)
        degust_id = parse_qs(urlparse(degust_config_url).query).get('code', [None]).pop()

        counts_file.metadata['degust_url'] = degust_config_url
        counts_file.save()

        # Now POST the settings to the Degust session, as per:
        # https://github.com/drpowell/degust/blob/master/FAQ.md#uploading-a-counts-file-from-the-command-line
        description = job.params.get('params').get('description', '')
        replicates = list(degust_conditions.items())
        init_select = []
        if len(conditions) >= 2:
            init_select = conditions[0:2]

        degust_settings = {
            'csv_format': False,
            'replicates': replicates,
            'fc_columns': [],
            'info_columns': ['Gene.ID', 'Chrom', 'Gene.Name', 'Biotype'],
            'analyze_server_side': True,
            'name': f'{description} (Laxy job: {job.id})',
            # 'primary_name': '',
            'init_select': init_select,
            # 'hidden_factor': [],
            'link_column': 'Gene.ID'
        }

        degust_settings_url = f'{degust_api_url}/degust/{degust_id}/settings'
        resp = requests.post(degust_settings_url, files={'settings': (None, json.dumps(degust_settings))})
        resp.raise_for_status()

        data = RedirectResponseSerializer(data={
            'status': browser.response.status_code,
            'redirect': degust_config_url})
        if data.is_valid():
            return Response(data=data.validated_data,
                            status=status.HTTP_200_OK)
        else:
            return HttpResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                reason="Error contacting Degust.")


class RemoteBrowseView(JSONView):
    renderer_classes = (JSONRenderer,)
    serializer_class = FileListing
    filter_backends = (RemoteFilesQueryParams,)
    api_docs_visible_to = 'public'

    # @method_decorator(cache_page(10 * 60))
    @view_config(response_serializer=FileListing)
    def get(self, request, version=None):
        """
        Returns a single level of a file/directory tree.
        Takes query parameters:
        * `url` - the URL (http[s]:// or ftp://) to retrieve.
        * `fileglob` - a glob pattern to filter returned files by (eg `*.csv`). Doesn't filter directories.
        eg

        **Request:**

        `GET http://laxy.io/api/v1/remote-browse/?url=ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR343/001/SRR3438011/&fileglob=*.gz`

        **Response:**
        ```json
        {
          "listing":[
                {
                  "type":"file",
                  "name":"SRR3438011_1.fastq.gz",
                  "location":"ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR343/001/SRR3438011/SRR3438011_1.fastq.gz",
                  "tags": []
                },
                {
                  "type":"directory",
                  "name":"FastQC_reports",
                  "location":"ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR343/001/SRR3438011/FastQC_reports/",
                  "tags": []
                },
                {
                  "type":"file",
                  "name":"data.tar",
                  "location":"ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR343/001/SRR3438011/data.tar.gz",
                  "tags": ['archive']
                }
            ]
        }
        ```

        <!--
        :param request:
        :type request:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """
        url = request.query_params.get('url', '').strip()
        fileglob = request.query_params.get('fileglob', '*')

        if url == '':
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="url query parameter is required.")

        # def _looks_like_archive(fn):
        #     archive_extensions = ['.tar']
        #     return any([fn.endswith(ext) for ext in archive_extensions])

        listing = []

        scheme = urlparse(url).scheme
        if scheme not in ['ftp', 'http', 'https']:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason=f"Unsupported scheme: {scheme}://")

        try:
            # We need to check the URL given is actually accessible
            if scheme in ['http', 'https']:
                resp = requests.head(url)
                resp.raise_for_status()
        except BaseException as exx:
            return JsonResponse({'remote_server_response': {'url': url,
                                                            'status': resp.status_code,
                                                            'reason': resp.reason}},
                                # TODO: When frontend interprets this better, use status 400 and let the frontend
                                #       report third-party response from the JSON blob
                                # status=status.HTTP_400_BAD_REQUEST,
                                status=resp.status_code,
                                reason=resp.reason)

        fn = Path(urlparse(url).path).name
        if is_archive_link(url, use_network=True) or fn.endswith('.manifest-md5'):
            try:
                archive_files = http_remote.get_tar_file_manifest(url)

                # Remove .manifest-md5 if present
                u = urlparse(url)
                url = u._replace(path=u.path.rstrip('.manifest-md5')).geturl()

                for f in archive_files:
                    filepath = f['filepath']
                    listing.append(dict(name=filepath,
                                        location=f'{url}#{filepath}',
                                        type='file',
                                        tags=['inside_archive']))
            except BaseException as ex:
                logger.debug(f'Unable to find archive manifest for {url}')
                logger.exception(ex)

                fn = Path(urlparse(url).path).name
                listing = [dict(name=fn,
                                location=f'{url}',
                                type='file',
                                tags=['archive'])]

        elif scheme == 'ftp':
            from fs import open_fs
            try:
                try:
                    # may raise fs.errors.RemoteConnectionError if FTP connection fails
                    ftp_fs = open_fs(url)
                except BaseException as exx:
                    msg = getattr(exx, 'msg', '')
                    return JsonResponse({'remote_server_response':
                                             {'url': url,
                                              'status': 500,
                                              'reason': msg}},
                                        # TODO: When frontend interprets this better, use status 400 and let the
                                        #       frontend report third-party response from the JSON blob
                                        # status=status.HTTP_400_BAD_REQUEST,
                                        status=500,
                                        reason=msg)

                for step in ftp_fs.walk(filter=[fileglob], search='breadth', max_depth=1):
                    listing.extend([dict(type='directory',
                                         name=i.name,
                                         location=f'{url.rstrip("/")}/{i.name}',
                                         tags=[])
                                    for i in step.dirs])
                    listing.extend([dict(type='file',
                                         name=i.name,
                                         location=f'{url.rstrip("/")}/{i.name}',
                                         tags=['archive'] if is_archive_link(i.name) else [])
                                    for i in step.files])
            except DirectoryExpected as ex:
                fn = Path(urlparse(url).path).name
                listing = [dict(name=fn,
                                location=f'{url}',
                                type='file',
                                tags=['archive'] if is_archive_link(fn) else [])]

        elif scheme == 'http' or scheme == 'https':
            _url = _check_content_size_and_resolve_redirects(url)

            try:
                text = render_page(_url)
            except MemoryError as ex:
                return HttpResponse(status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, reason=str(ex))
            except ValueError as ex:
                return HttpResponse(status=status.HTTP_400_BAD_REQUEST, reason=str(ex))

            _matched = False
            for matcher, link_parser_fn in LINK_SCRAPER_MAPPINGS:
                if isinstance(matcher, str) and matcher in _url:
                    _matched = True
                elif callable(matcher) and matcher(_url, text):
                    _matched = True

                if _matched:
                    listing = link_parser_fn(text, _url)
                    break

            if not _matched:
                return HttpResponse(status=status.HTTP_400_BAD_REQUEST, reason=f"No parser for this url: {_url}")

        # listing = pydash.sort_by(listing, ['type', 'name'])
        listing = multikeysort(listing, ['type', 'name'])
        item_list = FileListing({'listing': listing})
        return Response(item_list.data,
                        status=status.HTTP_200_OK)


def _get_or_create_drf_token(user):
    token_query = Token.objects.filter(user=user)
    if token_query.exists():
        token = token_query.first()
    else:
        token = Token.objects.create(user=user)

    return token


def _get_default_compute_resource(job: Job = None):
    if job is None:
        compute = ComputeResource.get_best_available()
    else:
        compute = _get_compute_resources_based_on_rules(job).first()

    if not compute:
        raise Exception(f"Cannot find available ComputeResource. None defined, or all offline.")

    return compute


def _get_compute_resources_based_on_rules(job: Job):
    # TODO: This should also incorporate per-user permissions to access specific ComputeResources
    # (eg with django-guardian and/or django-rules). We should be able to do a similar email domain test
    # with django-rules (eg write a can_use_compute(user, compute_resource) rule).
    # Ideally, our {domain: compute} mapping rules would be in the database so we can change them without
    # a restart.

    email_domain_allowed_compute = getattr(settings,
                                           'EMAIL_DOMAIN_ALLOWED_COMPUTE',
                                           {'*': ['*']})

    domain = job.owner.email.split('@')[-1]
    names = email_domain_allowed_compute.get(domain, None)
    if names is None:
        names = email_domain_allowed_compute.get('*', [])

    available_compute = (ComputeResource.objects
                         .filter(status=ComputeResource.STATUS_ONLINE)
                         .order_by('-priority'))

    if '*' in names:
        return available_compute

    allowed_compute = available_compute.filter(name__in=names).order_by('-priority')

    if not allowed_compute.exists():
        raise Exception(f"Cannot find allowed ComputeResource for this email domain ({domain}).")

    return allowed_compute
