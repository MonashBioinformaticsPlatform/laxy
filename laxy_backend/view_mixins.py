from io import StringIO, BytesIO
from typing import List, Union

import csv
import json
import rows

from rest_framework.request import Request
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.schemas import SchemaGenerator
from rest_framework.renderers import JSONRenderer, SchemaJSRenderer, CoreJSONRenderer
from rest_framework.parsers import JSONParser, BaseParser

from drf_openapi.utils import view_config


class JSONView(APIView):
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

    # TODO: This should be replaced by proper use of permission_classes
    #       on views (eg with django-guardian).
    def _check_owner(self, obj):
        user = self.request.user
        if user.is_superuser:
            return obj

        if hasattr(obj, 'owner'):
            if user != obj.owner:
                return None
                # return HttpResponse(status=status.HTTP_403_FORBIDDEN,
                #                     reason="Permission denied.")
        return obj

    def get_obj(self, uuid):
        try:
            # if we are using a native UUIDField on the model (rather than a
            # CharField) we must first turn the UUID Base64 (or Base62) string
            # into an actual uuid.UUID instance to do the query.
            # uuid = Job.b64uuid_to_uuid(uuid)
            ModelClass = self.Meta.model
            obj = ModelClass.objects.get(id=uuid)
            return self._check_owner(obj)

        except (ModelClass.DoesNotExist, ValueError):
            return None


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
    def get(self, request: Request, uuid: str) -> Response:
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
        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.Meta.serializer(obj)
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
        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if 'id' in request.data:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="id cannot be updated")

        serializer = self.Meta.serializer(obj,
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
            serializer_class=None) -> Union[Response, HttpResponse]:
        """
        Replacing an existing resource.
        (Creating a new resource via specifying a UUID is not allowed)

        <!--
        :param request:
        :type request:
        :param uuid:
        :type uuid:
        :return:
        :rtype:
        -->
        """
        if serializer_class is None:
            serializer_class = self.Meta.serializer

        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if 'id' in request.data:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST,
                                reason="id cannot be updated")

        serializer = serializer_class(obj, data=request.data,
                                      context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
            # return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


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
        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

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

        serializer = self.Meta.serializer(data=request.data,
                                          context={'request': request})
        if serializer.is_valid():
            obj = serializer.save()
            # 200 status code since we include the resulting entity in the body
            # We'd do 201 if we only returned a link to the entity in the body
            # and a Location header.
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/201
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
