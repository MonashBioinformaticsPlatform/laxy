from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.response import Response

from .view_mixins import JSONView, GetMixin, PatchMixin, DeleteMixin, PostMixin
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Job
from .serializers import EventSerializer
from . import tasks


def _get_object_auth_header(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    secret = None
    if 'ObjectToken ' in auth_header:
        secret = auth_header.split('ObjectToken ')[1].strip()
    return secret


def _get_event_target_object(data):
    content_type = data.get('content_type', None)
    object_id = data.get('object_id', None)
    ct = ContentType.objects.get(app_label='laxy_backend',
                                 model=content_type)
    obj = ct.get_object_for_this_type(id=object_id)
    return obj


class Events(JSONView):
    permission_classes = (AllowAny,)

    # class Meta:
    #     model = Event
    #     serializer = EventSerializer

    @method_decorator(csrf_exempt)
    def post(self, request):

        # TODO: check 'secret' is valid in the header:
        #       Authorization: ObjectToken 3riofj3rfoi3ncoi3wfo..
        #
        # Should this token be a JWT with claims to the object and
        # an expiry ? This would avoid needing to expire keys in the
        # database for old stale jobs.

        serializer = EventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        event_type = data.get('event_type')

        if event_type == 'job_complete':
            try:
                secret = _get_object_auth_header(request)
                if secret is None:
                    return Response({}, status=status.HTTP_401_UNAUTHORIZED)

                job = _get_event_target_object(data)
                if not isinstance(job, Job):
                    return Response({}, status=status.HTTP_400_BAD_REQUEST)

                if job.secret != secret:
                    return Response({}, status=status.HTTP_401_UNAUTHORIZED)

                if job.secret and job.status == Job.STATUS_RUNNING:
                    job.status = Job.STATUS_COMPLETE
                    job.secret = None
                    job.save()

                    task_data = {'compute_resource_id': job.compute_resource.id}
                    if job.compute_resource.disposable:
                        tasks.stop_cluster.apply_async(
                            args=(task_data,))

                else:
                    return Response({'message': 'Job is complete and cannot'
                                                'be updated.'},
                                    status=status.HTTP_403_FORBIDDEN)

                return Response({}, status=status.HTTP_204_NO_CONTENT)
            except:
                return Response({}, status=status.HTTP_400_BAD_REQUEST)

        return Response({}, status=status.HTTP_400_BAD_REQUEST)
