from collections import OrderedDict

import json_merge_patch
import jsonpatch
from io import StringIO, BytesIO
from rest_framework.generics import GenericAPIView
from rest_framework.serializers import BaseSerializer
from typing import List, Union
import functools

import csv
import json
import rows

from rest_framework.request import Request
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, NotFound
from rest_framework.views import APIView
from rest_framework.schemas import SchemaGenerator
from rest_framework.renderers import JSONRenderer, SchemaJSRenderer, CoreJSONRenderer
from rest_framework.parsers import JSONParser, BaseParser

from drf_openapi.utils import view_config

import logging

from .util import get_content_type

logger = logging.getLogger(__name__)


def etag_headers(method):
    """
    A decorator that adds `ETag` and `Last-Modified` headers to `.get` method responses if not already present.
    Intended to be use with Timestamped models (or any object with a modified_time field).
    """

    @functools.wraps(method)
    def add_etag_headers_to_response(*args, **kwargs):
        response = method(*args, **kwargs)
        if len(args) > 0:
            obj = args[0].get_object()
            if hasattr(obj, 'modified_time'):
                if response.get('Last-Modified', None) is None:
                    response['Last-Modified'] = obj.modified_time.strftime(
                        "%a, %d %b %Y %H:%M:%S GMT")
                if response.get('ETag', None) is None:
                    # NGINX strips out 'strong' ETags by default, so we use a weak (W/) ETag
                    response['ETag'] = f'W/"{obj.modified_time.isoformat()}"'
        return response

    return add_etag_headers_to_response


class JSONView(GenericAPIView):
    lookup_url_kwarg = 'uuid'
    # lookup_field = 'id' # same as default, 'pk'

    # renderer_classes = (JSONRenderer, SchemaJSRenderer, CoreJSONRenderer,)
    # renderer_classes = (CoreJSONRenderer,)
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    api_docs_visible_to = 'public'

    # def get(self, request):
    #     generator = SchemaGenerator()
    #     schema = generator.get_schema(request=request)
    #
    #     return Response(schema)

    # DEPRECATED, in favor of using permission_classes on views (eg with django-guardian).
    # def _check_owner(self, obj):
    #     user = self.request.user
    #     if user.is_superuser:
    #         return obj
    #
    #     if hasattr(obj, 'owner'):
    #         if user != obj.owner:
    #             return None
    #             # return HttpResponse(status=status.HTTP_403_FORBIDDEN,
    #             #                     reason="Permission denied.")
    #     return obj

    # DEPRECATED, in favor of self.get_object() from the parent class (GenericAPIView)
    # def get_obj(self, uuid):
    #     try:
    #         # if we are using a native UUIDField on the model (rather than a
    #         # CharField) we must first turn the UUID Base64 (or Base62) string
    #         # into an actual uuid.UUID instance to do the query.
    #         # uuid = Job.b64uuid_to_uuid(uuid)
    #         queryset = self.get_queryset()
    #         obj = queryset.get(id=uuid)
    #         # return self._check_owner(obj)
    #         return obj
    #
    #     except (queryset.model.DoesNotExist, ValueError):
    #         return None

    def permission_denied(self, request, message=None):
        """
        If request is not permitted, determine what kind of exception to raise.

        Unlike the default DRF implementation, we don't raise PermissionDenied since
        this is an information leak - an attacker could discover that a particular
        object UUID exists based on 403 vs. 404 status code. By always returning 404,
        they can't learn if the object exists or if they just don't have access.
        """
        if request.authenticators and not request.successful_authenticator:
            raise NotAuthenticated()

        logger.info(f"Permission denied (but sending 404 Not Found): {request.get_full_path()}")
        # raise PermissionDenied(detail=message)
        raise NotFound()


class CSVTextParser(BaseParser):
    """
    A CSV parser for DRF APIViews.

    Based on the RFC 4180 text/csv MIME type, but extended with
    a dialect.
    https://tools.ietf.org/html/rfc4180
    """
    media_type = 'text/csv'

    def parse(self, stream, media_type=None, parser_context=None) -> List[List]:
        """
        Return a list of lists representing the rows of a CSV file.
        """
        # return list(csv.reader(stream, dialect='excel'))

        media_type_params = dict([param.strip().split('=') for param in media_type.split(';')[1:]])
        charset = media_type_params.get('charset', 'utf-8')
        dialect = media_type_params.get('dialect', 'excel')
        txt = stream.read().decode(charset)
        csv_table = list(csv.reader(txt.splitlines(), dialect=dialect))
        return csv_table


class RowsCSVTextParser(BaseParser):
    """
    A CSV parser for DRF APIViews, using the `rows` Python library for parsing.

    Based on the RFC 4180 text/csv MIME type.

    https://tools.ietf.org/html/rfc4180
    """
    media_type = 'text/csv'

    def parse(self, stream, media_type=None, parser_context=None) -> List[dict]:
        """
        Return a list of lists representing the rows of a CSV file.
        """
        media_type_params = dict([param.strip().split('=') for param in media_type.split(';')[1:]])
        charset = media_type_params.get('charset', 'utf-8')
        dialect = media_type_params.get('dialect', 'excel')
        txt = stream.read()
        try:
            table = rows.import_from_csv(BytesIO(txt),
                                         encoding=charset,
                                         dialect=dialect,
                                         skip_header=False)
        except Exception as ex:
            raise ex
        table = json.loads(rows.export_to_json(table))
        return table


class GetMixin:
    def get(self, request: Request, uuid: str) -> Union[Response, HttpResponse]:
        """
        Returns info about a model instance retrieved by UUID.

        <!--
        :param request: The request object.
        :type request:
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype:
        -->
        """
        obj = self.get_object()
        if hasattr(self, 'response_serializer'):
            serializer = self.response_serializer(obj)
        else:
            serializer = self.get_serializer(instance=obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PatchMixin:
    def patch(self,
              request: Request,
              uuid: str) -> Union[Response, HttpResponse]:
        """

        PATCH: https://tools.ietf.org/html/rfc5789

        <!--
        :param request:
        :type request:
        :param uuid:
        :type uuid:
        :return:
        :rtype:
        -->
        """
        obj = self.get_object()

        if 'id' in request.data:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="id cannot be updated")

        # TODO: Support self.request_serializer and self.response_serializer here
        #       Maybe override get_serializer in JSONView ?
        serializer = self.get_serializer(instance=obj,
                                         data=request.data,
                                         context={'request': request},
                                         partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
            # return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class PutMixin:
    def put(self,
            request: Request,
            uuid: str,
            serializer_class: Union[None, BaseSerializer] = None) -> Union[Response, HttpResponse]:
        """
        Replacing an existing resource.
        (Creating a new resource via specifying a UUID is not allowed)

        <!--
        :param request:
        :type request:
        :param uuid:
        :type uuid:
        :param serializer_class: Override default serializer_class (don't use the serializer from the base class)
        :type serializer_class: None | rest_framework.serializers.BaseSerializer
        :return:
        :rtype:
        -->
        """

        obj = self.get_object()

        if 'id' in request.data:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="id cannot be updated")

        # TODO: Support self.request_serializer and self.response_serializer instead
        #       of this serializer_class keyword arg
        #       Maybe override get_serializer in JSONView ?
        if serializer_class is None:
            serializer_class = self.get_serializer_class()

        serializer = serializer_class(instance=obj, data=request.data,
                                      context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
            # return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


# TODO: This would be cleaner as a decorator to a patch method, similar to @etag_headers
class JSONPatchMixin:
    def _is_json_patch_content_type(self, request):
        content_type = get_content_type(request)
        return content_type in ['application/merge-patch+json',
                                'application/json-patch+json']

    def _patch_request(self, request: Request, obj=None, field='metadata'):
        content_type = get_content_type(request)

        if obj is None:
            obj = self.get_object()

        metadata = request.data.get(field, None)
        if metadata is not None:
            if isinstance(metadata, list):
                patch = [OrderedDict(op) for op in metadata]
            else:
                patch = OrderedDict(metadata)

            # https://tools.ietf.org/html/rfc7386
            if content_type == 'application/merge-patch+json':
                request.data[field] = json_merge_patch.merge(
                    OrderedDict(getattr(obj, field)),
                    patch)
            # https://tools.ietf.org/html/rfc6902
            if content_type == 'application/json-patch+json':
                request.data[field] = jsonpatch.apply_patch(
                    OrderedDict(getattr(obj, field)),
                    patch)

            logger.debug(f"_try_json_patch - patched {field}: {request.data}")

        return request

    def _try_json_patch(self, request: Request, obj=None, field='metadata'):
        """
        Partial update of the 'metadata' field on an object.

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
        :return:
        :rtype:
        -->
        """

        # content_type = get_content_type(request)
        if self._is_json_patch_content_type(request):
            if obj is None:
                obj = self.get_object()
            if obj is None:
                return Response(status=status.HTTP_404_NOT_FOUND)

            if 'id' in request.data:
                return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                    reason="id cannot be updated")

            if not hasattr(obj, field):
                return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                    reason=f"Invalid field for this object type: {field}")

            request = self._patch_request(request, obj=obj, field=field)

            if hasattr(self, 'request_serializer'):
                serializer_method = self.request_serializer
            else:
                serializer_method = self.get_serializer
            serializer = serializer_method(instance=obj,
                                           data=request.data,
                                           context={'request': request},
                                           partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

        return None


class DeleteMixin:
    def delete(self,
               request: Request,
               uuid: str) -> Response:
        """
        Deletes the object specified via UUID.

        <!--
        :param request:
        :type request:
        :param job_id:
        :type job_id:
        :return:
        :rtype:
        -->
        """
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostMixin:
    def post(self, request: Request) -> Response:
        """
        Create a new model instance. UUIDs are autoassigned.

        <!--
        :param request: The request object.
        :type request:
        :return: The response object.
        :rtype:
        -->
        """

        # TODO: Support self.request_serializer and self.response_serializer overrides here (as per GetMixin)
        #       Maybe override get_serializer in JSONView ?
        serializer = self.get_serializer(data=request.data,
                                         context={'request': request})
        if serializer.is_valid():
            obj = serializer.save()
            # 200 status code since we include the resulting entity in the body
            # We'd do 201 if we only returned a link to the entity in the body
            # and a Location header.
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/201
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
