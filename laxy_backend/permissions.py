from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import permissions
from .models import AccessToken, Job, File, FileSet

import logging

logger = logging.getLogger(__name__)

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def _get_content_types(*models):
    return [ContentType.objects.get_for_model(m) for m in models]


def token_is_valid(token: str, obj_id: str):
    """
    Return True is an access token is valid for the given object (by ID).

    :param token:
    :type token:
    :param obj_id:
    :type obj_id:
    :return: True if the token is valid for this object
    :rtype: bool
    """

    return (
        AccessToken.objects.filter(
            token=token,
            # content_type__in=self.valid_content_types,
            object_id=obj_id,
        )
        .filter(Q(expiry_time__gt=datetime.now()) | Q(expiry_time=None))
        .exists()
    )


class HasReadonlyObjectAccessToken(permissions.BasePermission):
    # We don't check content_type, but rely on uniqueness of object UUID primary keys
    # valid_content_types = _get_content_types(Job, File, FileSet)

    def has_object_permission(self, request, view, obj):
        # These tokens are only ever for readonly access, so they are never valid
        # for 'unsafe' HTTP methods
        if request.method not in SAFE_METHODS:
            return False

        token = request.query_params.get("access_token", None)
        if not token:
            token = request.COOKIES.get(f"access_token__{obj.id}", None)

        if not token:
            return False

        is_valid = token_is_valid(token, obj.id)
        if not is_valid:
            logger.error(
                f"Invalid or expired AccessToken {token} used when attempting to access {obj.id}"
            )
        return is_valid


class HasAccessTokenForEventLogSubject(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        token = request.query_params.get("access_token", None)
        obj_id = request.query_params.get("object_id", None)  # the Job.id
        if token and obj_id:
            return token_is_valid(token, obj_id)

        return False


class FileSetHasAccessTokenForJob(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: FileSet):
        token = request.query_params.get("access_token", None)
        if token:
            jobs = obj.jobs()
            for job in jobs:
                if token_is_valid(token, job.id):
                    return True
        return False


class FileHasAccessTokenForJob(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: File):
        token = request.query_params.get("access_token", None)
        if token:
            jobs = obj.fileset.jobs()
            for job in jobs:
                if token_is_valid(token, job.id):
                    return True
        return False


class IsSuperuser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        return False


def is_owner(user, obj):
    owner_field_name = getattr(obj, "owner_field_name", "owner")
    if hasattr(obj, owner_field_name) and (user == getattr(obj, owner_field_name)):
        return True

    return False


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        return is_owner(user, obj)
