from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from rest_framework import permissions
from .models import AccessToken, Job, File, FileSet

import logging

logger = logging.getLogger(__name__)


def _get_content_types(*models):
    return [ContentType.objects.get_for_model(m) for m in models]


class HasObjectAccessToken(permissions.BasePermission):
    # We don't check content_type, but rely on uniqueness of object UUID primary keys
    # valid_content_types = _get_content_types(Job, File, FileSet)

    def has_object_permission(self, request, view, obj):
        token = request.query_params.get('access_token', None)
        if not token:
            return False
        valid_token = AccessToken.objects.filter(token=token,
                                                 object_id=obj.id,
                                                 # content_type__in=self.valid_content_types,
                                                 expiry_time__gt=datetime.now()).exists()
        return valid_token


class IsSuperuser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        return False


def is_owner(user, obj):
    owner_field_name = getattr(obj, 'owner_field_name', 'owner')
    if ((hasattr(obj, owner_field_name) and user == getattr(obj, owner_field_name))
            or user.is_superuser):
        return True

    return False


class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        return is_owner(user, obj)
