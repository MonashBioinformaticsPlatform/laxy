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
import pandas as pd

from rest_framework.request import Request
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, NotFound
from rest_framework.views import APIView
from rest_framework.schemas import SchemaGenerator
from rest_framework.renderers import JSONRenderer, SchemaJSRenderer, CoreJSONRenderer
from rest_framework.parsers import JSONParser, BaseParser

# from drf_openapi.utils import view_config  # Removed - no longer using drf_openapi

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
            if hasattr(obj, "modified_time"):
                if response.get("Last-Modified", None) is None:
                    response["Last-Modified"] = obj.modified_time.strftime(
                        "%a, %d %b %Y %H:%M:%S GMT"
                    )
                if response.get("ETag", None) is None:
                    # NGINX strips out 'strong' ETags by default, so we use a weak (W/) ETag
                    response["ETag"] = f'W/"{obj.modified_time.isoformat()}"'
        return response

    return add_etag_headers_to_response


class JSONView(GenericAPIView):
    lookup_url_kwarg = "uuid"
    # lookup_field = 'id' # same as default, 'pk'

    # renderer_classes = (JSONRenderer, SchemaJSRenderer, CoreJSONRenderer,)
    # renderer_classes = (CoreJSONRenderer,)
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    api_docs_visible_to = "public"

    # def get(self, request):
    #     generator = SchemaGenerator()
    #     schema = generator.get_schema(request=request)
    #
    #     return Response(schema)

    def get_request_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input (from the Request).
        """
        serializer_class = getattr(
            self, "request_serializer", self.get_serializer_class()
        )
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_response_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing output (for the Response).
        """
        serializer_class = getattr(
            self, "response_serializer", self.get_serializer_class()
        )
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def permission_denied(self, request, message=None, code=None):
        """
        If request is not permitted, determine what kind of exception to raise.

        Unlike the default DRF implementation, we don't raise PermissionDenied since
        this is an information leak - an attacker could discover that a particular
        object UUID exists based on 403 vs. 404 status code. By always returning 404,
        they can't learn if the object exists or if they just don't have access.
        """
        if request.authenticators and not request.successful_authenticator:
            raise NotAuthenticated()

        logger.info(
            f"Permission denied (but sending 404 Not Found): {request.get_full_path()}"
        )
        # raise PermissionDenied(detail=message)
        raise NotFound()


class CSVTextParser(BaseParser):
    """
    A CSV parser for DRF APIViews.

    Based on the RFC 4180 text/csv MIME type, but extended with
    a dialect.
    https://tools.ietf.org/html/rfc4180
    """

    media_type = "text/csv"

    def parse(self, stream, media_type=None, parser_context=None) -> List[List]:
        """
        Return a list of lists representing the rows of a CSV file.
        """
        # return list(csv.reader(stream, dialect='excel'))

        media_type_params = dict(
            [param.strip().split("=") for param in media_type.split(";")[1:]]
        )
        charset = media_type_params.get("charset", "utf-8-sig")
        # Override utf-8 encoding to always handle byte order mark transparently
        if charset == "utf-8":
            charset == "utf-8-sig"
        dialect = media_type_params.get("dialect", "excel")
        txt = stream.read().decode(charset)

        # cheating
        # def remove_prefix(s, prefix):
        #    return s[len(prefix):] if s.startswith(prefix) else s
        # txt = remove_prefix(txt, "\ufeff")

        csv_table = list(csv.reader(txt.splitlines(), dialect=dialect))
        return csv_table


class CSVTextParserPandas(BaseParser):
    """
    A CSV/TSV parser for DRF APIViews, using the `pandas` library for parsing.

    Based on the RFC 4180 text/csv MIME type.

    https://tools.ietf.org/html/rfc4180
    """

    media_type = "text/csv"

    def parse(self, stream, media_type=None, parser_context=None) -> List[dict]:
        """
        Return a list of lists representing the rows of a CSV file.
        """
        media_type_params = dict(
            [param.strip().split("=") for param in media_type.split(";")[1:]]
        )
        charset = media_type_params.get("charset", "utf-8")
        dialect = media_type_params.get("dialect", "excel")
        txt = stream.read()
        try:
            table = json.loads(
                pd.read_table(BytesIO(txt), encoding=charset, dialect=dialect).to_json(
                    orient="records"
                )
            )
        except Exception as ex:
            raise ex
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
        serializer = self.get_response_serializer(instance=obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PatchMixin:
    def patch(self, request: Request, uuid: str) -> Union[Response, HttpResponse]:
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

        if "id" in request.data:
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST, reason="id cannot be updated"
            )

        serializer = self.get_request_serializer(
            instance=obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            # We currently return an empty response to PATCH.
            # AFAIK there's no strict standard/RFC around what to return in the
            # body of the response (if we did return 200 instead of 204).
            # One way is some convention as part of the Content-Type header.
            # WebDAV does it with a
            #   "Prefer: return=representation" or
            #   "Prefer: return=minimal"
            # header.
            #   https://greenbytes.de/tech/webdav/rfc7240.html#return
            # Empty + status 204 is fine unless we have need for something else.
            #
            # return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PutMixin:
    def put(
        self,
        request: Request,
        uuid: str,
        serializer_class: Union[None, BaseSerializer] = None,
    ) -> Union[Response, HttpResponse]:
        """
        Replace an existing resource.
        (Creating a new resource via specifying a UUID is not allowed,
        since UUIDs are always automatically assigned)

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

        if "id" in request.data:
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST, reason="id cannot be updated"
            )

        serializer = self.get_request_serializer(
            instance=obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

            # This is also acceptable, but not required.
            # If the server modifies/adds fields in the PUT request.data,
            # it might make sense to do this so the client gets an accurate
            # state of the updated object.
            # return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# TODO: This would be cleaner as a decorator to a patch method, similar to @etag_headers
class JSONPatchMixin:
    def _is_json_patch_content_type(self, request):
        content_type = get_content_type(request)
        return content_type in [
            "application/merge-patch+json",
            "application/json-patch+json",
        ]

    def _patch_request(self, request: Request, obj=None, field="metadata"):
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
            if content_type == "application/merge-patch+json":
                request.data[field] = json_merge_patch.merge(
                    OrderedDict(getattr(obj, field)), patch
                )
            # https://tools.ietf.org/html/rfc6902
            if content_type == "application/json-patch+json":
                request.data[field] = jsonpatch.apply_patch(
                    OrderedDict(getattr(obj, field)), patch
                )

            logger.debug(f"_try_json_patch - patched {field}: {request.data}")

        return request

    def _try_json_patch(self, request: Request, obj=None, field="metadata"):
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

            if "id" in request.data:
                return HttpResponse(
                    status=status.HTTP_400_BAD_REQUEST, reason="id cannot be updated"
                )

            if not hasattr(obj, field):
                return HttpResponse(
                    status=status.HTTP_400_BAD_REQUEST,
                    reason=f"Invalid field for this object type: {field}",
                )

            request = self._patch_request(request, obj=obj, field=field)
            serializer = self.get_request_serializer(
                instance=obj, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

        return None


class DeleteMixin:
    def delete(self, request: Request, uuid: str) -> Response:
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

        # serializer = self.get_serializer(
        #     data=request.data, context={"request": request}
        # )

        # if hasattr(self, "request_serializer"):
        #     req_serializer = self.request_serializer(data=request.data)
        # else:
        #     req_serializer = self.get_serializer(data=request.data)

        # if hasattr(self, "response_serializer"):
        #     resp_serializer = self.response_serializer(instance=obj)
        # else:
        #     resp_serializer = self.get_serializer(instance=obj)
        req_serializer = self.get_request_serializer(data=request.data)

        if req_serializer.is_valid():
            obj = req_serializer.save()

            resp_serializer = self.get_response_serializer(instance=obj)
            # 200 status code since we include the resulting entity in the body
            # We'd do 201 if we only returned a link to the entity in the body
            # and a Location header.
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/201
            return Response(resp_serializer.data, status=status.HTTP_200_OK)

        return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
