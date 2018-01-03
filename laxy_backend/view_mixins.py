from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.schemas import SchemaGenerator
from rest_framework.renderers import JSONRenderer, SchemaJSRenderer, CoreJSONRenderer

from drf_openapi.utils import view_config


class JSONView(APIView):
    # renderer_classes = (JSONRenderer, SchemaJSRenderer, CoreJSONRenderer,)
    # renderer_classes = (CoreJSONRenderer,)
    renderer_classes = (JSONRenderer,)
    api_docs_visible_to = 'public'

    # def get(self, request):
    #     generator = SchemaGenerator()
    #     schema = generator.get_schema(request=request)
    #
    #     return Response(schema)

    def get_obj(self, uuid):
        try:
            # if we are using a native UUIDField on the model (rather than a
            # CharField) we must first turn the UUID Base64 (or Base62) string
            # into an actual uuid.UUID instance to do the query.
            # uuid = Job.b64uuid_to_uuid(uuid)
            ModelClass = self.Meta.model
            return ModelClass.objects.get(id=uuid)
        except (ModelClass.DoesNotExist, ValueError):
            return None


class GetMixin:
    def get(self, request, uuid):
        """
        Returns info about a model instance retrieved by UUID.

        :param request: The request object.
        :type request:
        :param uuid: The URL-encoded UUID.
        :type uuid: str
        :return: The response object.
        :rtype:
        """
        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.Meta.serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PatchMixin:
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

        serializer = self.Meta.serializer(obj,
                                          data=request.data,
                                          partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
            # return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class DeleteMixin:
    def delete(self, request, uuid):
        """

        :param request:
        :type request:
        :param job_id:
        :type job_id:
        :return:
        :rtype:

        """
        obj = self.get_obj(uuid)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        obj.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class PostMixin:
    def post(self, request):
        """
        Create a new model instance. UUIDs are autoassigned.

        :param request: The request object.
        :type request:
        :return: The response object.
        :rtype:
        """

        serializer = self.Meta.serializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
