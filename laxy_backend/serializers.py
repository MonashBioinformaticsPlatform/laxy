import json
from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType
from pathlib import Path
from urllib.parse import urlparse

import pydash
from django.db import transaction
from rest_framework import serializers
from django.core.validators import URLValidator
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.fields import CurrentUserDefault
from typing import Sequence

from drf_openapi.entities import VersionedSerializers
from http.client import responses as response_code_messages

from laxy_backend.models import SampleCart, PipelineRun, File, FileSet
from laxy_backend.util import unique, is_valid_laxy_sftp_url
from . import models

import logging

logger = logging.getLogger(__name__)

default_status_codes = (400, 401, 403, 404)


def status_codes(*codes):
    if not codes:
        codes = default_status_codes
    return dict([(c, response_code_messages[c]) for c in codes])


# TODO: Swagger docs (drf_openapi) lists JSONField type as string.
#       So we use our this class to serialize arbitrary JSON instead.
#       It appears as the the correct field type in the docs.
#       Maybe drf_openapi needs a fix ?
class SchemalessJsonResponseSerializer(serializers.Serializer):
    """
    We use this serializer anywhere we want to accept a schemaless blob of JSON.
    """

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        instance = validated_data
        return instance

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = json.loads(data, object_pairs_hook=OrderedDict)
        data = OrderedDict(data)
        if json.loads(json.dumps(data), object_pairs_hook=OrderedDict) != data:
            msg = "Invalid JSON, round-trip serialization failed"
            raise ValidationError(msg)
        return data

    def to_representation(self, obj):
        return obj


class BaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        read_only_fields = ("id",)

    def uuid(self, obj):
        if hasattr(obj, "uuid"):
            return obj.uuid()
        else:
            return obj.id

    def _set_owner(self, obj):
        """
        Set the owner (User) of the model instance (`obj`), based
        on the user making the request.
        """
        if self.context:
            user = self.context.get("request").user
            if user and hasattr(obj, "owner"):
                obj.owner = user

        return obj

    def create(self, validated_data):
        obj = self.Meta.model.objects.create(**validated_data)
        # If the request is provided as part of the context
        # passed to the serializer, assign it as the owner
        # of the model
        obj = self._set_owner(obj)
        obj.save()
        return obj

    def _update_attrs(self, instance, validated_data):
        """
        Updates the non-readonly attributes on a model instance with
        the given validated_data (dictionary) values.

        :param instance: The model instance to update
        :type instance: django.db.models.Model
        :param validated_data: The new data that will replace attribute
                               values in instance.
        :type validated_data: dict
        :return: The updated model instance.
        :rtype: django.db.models.Model
        """
        for k, v in validated_data.items():
            if k not in getattr(self.Meta, "read_only_fields", []):
                setattr(instance, k, v)
        return instance


class PatchSerializerResponse(serializers.Serializer):
    """
    A generic PATCH response serializer, which should generally be 204 status
    code on success with no response body. This primarily exists to present
    the correct status codes in the drf_openapi Swagger docs.
    """

    class Meta:
        fields = ()
        read_only_fields = ("id",)
        error_status_codes = status_codes(*default_status_codes, 204)


class PutSerializerResponse(serializers.Serializer):
    """
    A generic PUT response serializer, which should generally be 204 status
    code on success with no response body. This primarily exists to present
    the correct status codes in the drf_openapi Swagger docs.
    """

    class Meta:
        fields = ()
        read_only_fields = ("id",)
        error_status_codes = status_codes(*default_status_codes, 204)


class SystemStatusSerializer(BaseModelSerializer):
    class Meta:
        model = models.SystemStatus
        fields = (
            "status",
            "message",
            "long_message",
            "link_url",
            "start_time",
            "end_time",
        )


class PingResponseSerializer(serializers.Serializer):
    system_status = SystemStatusSerializer(
        required=False, read_only=True, allow_null=True
    )
    version = serializers.CharField(max_length=255, required=False)
    env = serializers.CharField(max_length=255, required=False)


class FileSerializer(BaseModelSerializer):
    name = serializers.CharField(max_length=255, required=False)
    path = serializers.CharField(max_length=4096, required=False)
    location = serializers.CharField(
        max_length=2048, validators=[models.URIValidator()]
    )
    fileset = serializers.PrimaryKeyRelatedField(
        queryset=FileSet.objects.all(), required=False
    )
    type_tags = serializers.ListField(default=[], required=False)
    # metadata = serializers.JSONField()
    metadata = SchemalessJsonResponseSerializer(
        required=False
    )  # becomes OpenAPI 'object' type

    class Meta:
        model = models.File
        fields = (
            "id",
            "owner",
            "name",
            "path",
            "location",
            "checksum",
            "fileset",
            "type_tags",
            "deleted",
            "metadata",
        )
        read_only_fields = (
            "id",
            "owner",
        )
        error_status_codes = status_codes()

    def create(self, validated_data):
        location = validated_data.get("location", None)
        scheme = urlparse(location).scheme.lower()
        if scheme == "laxy+sftp" and not is_valid_laxy_sftp_url(location):
            raise ValidationError(
                "Invalid laxy+ftp:// URL (does ComputeResource exist ?)"
            )

        f = models.File.objects.create(**validated_data)
        f.save()
        return f

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = self._update_attrs(instance, validated_data)
        for field in getattr(self.Meta.model.ExtraMeta, "patchable_fields", []):
            if hasattr(instance, field):
                new_value = validated_data.get(field, getattr(instance, field))
                setattr(instance, field, new_value)
        instance.save()
        return instance


class FileSerializerPostRequest(FileSerializer):
    class Meta(FileSerializer.Meta):
        fields = (
            "name",
            "path",
            "location",
            "checksum",
            "fileset",
            "type_tags",
            "metadata",
        )


class FileBulkRegisterSerializer(FileSerializer):
    class Meta(FileSerializer.Meta):
        fields = ("name", "path", "location", "checksum", "type_tags", "metadata")

    def to_internal_value(self, data):
        if isinstance(data.get("type_tags", ""), str):
            data["type_tags"] = data["type_tags"].replace(" ", "").split(",")
        if "filepath" in data:
            data["name"] = Path(data["filepath"]).name
            data["path"] = str(Path(data["filepath"]).parent)
            del data["filepath"]

        # Trim any whitespace from ends of values
        for field in self.Meta.fields:
            if field in data and isinstance(data[field], str):
                data[field] = data[field].strip()
            if field in data and isinstance(data[field], list):
                data[field] = [item.strip() for item in data[field]]

        return data

    # Only add type_tags, don't replace list
    # def update(self, instance: File, validated_data):
    #     validated_data['type_tags'].extend(instance.type_tags)
    #     validated_data['type_tags'] = unique(validated_data['type_tags'])
    #     instance = self._update_attrs(instance, validated_data)
    #     instance.save()
    #     return instance


# naming is hard
class JobFileSerializerCreateRequest(FileSerializer):
    location = serializers.CharField(
        max_length=2048, validators=[models.URIValidator()], required=False
    )

    class Meta(FileSerializer.Meta):
        fields = ("location", "checksum", "type_tags", "metadata")


class FileSetSerializer(BaseModelSerializer):

    files = FileSerializer(many=True, required=False, allow_null=True)

    # This lists only only IDs
    # files = serializers.PrimaryKeyRelatedField(many=True,
    #                                            queryset=File.objects.all())

    class Meta:
        model = models.FileSet
        fields = (
            "id",
            "name",
            "path",
            "owner",
            "files",
        )
        read_only_fields = (
            "id",
            "owner",
        )
        depth = 0
        error_status_codes = status_codes()


class FileSerializerOptionalLocation(FileSerializer):
    """
    Allows the `location` field to be omitted - intended to be
    used when we want to be able to refer to a list of new files
    where location would be required, or a list of existing files
    using `id` only.
    """

    id = serializers.CharField(max_length=24, required=False)
    location = serializers.CharField(
        required=False,
        allow_null=False,
        allow_blank=False,
        max_length=2048,
        validators=[models.URIValidator()],
    )


class FileSetSerializerPostRequest(FileSetSerializer):
    class Meta(FileSetSerializer.Meta):
        fields = (
            "id",
            "name",
            "path",
            "files",
        )

    files = FileSerializerOptionalLocation(many=True, required=False, allow_null=True)

    @transaction.atomic
    def create(self, validated_data):
        """

        :param validated_data:
        :type validated_data:
        :return:
        :rtype:
        """
        files_data = validated_data.pop("files", [])

        fset = models.FileSet.objects.create(**validated_data)
        fset = self._set_owner(fset)

        # We create new file objects if the `files` list has details other than
        # the id set. If only the id is set, we assume it's an existing file
        # and use that.

        for f in files_data:
            f_id = f.get("id", None)
            if not f_id:
                fobj = models.File.objects.create(**f)
                fobj.owner = fset.owner
            else:
                try:
                    fobj = models.File.objects.get(id=f_id)
                except File.DoesNotExist:
                    raise File.DoesNotExist(f"File {f_id} does not exist.")

                if fobj.owner != fset.owner:
                    raise PermissionDenied(
                        detail="Attempt to add Files not owned by the FileSet owner disallowed."
                    )

            fset.add(fobj)

        return fset


class SampleCartSerializer(BaseModelSerializer):
    # samples = serializers.JSONField(required=True)
    # samples = SchemalessJsonResponseSerializer(required=True)
    samples = serializers.ListField(required=True)

    class Meta:
        model = models.SampleCart
        fields = ("id", "name", "owner", "samples")
        read_only_fields = (
            "id",
            "owner",
        )
        error_status_codes = status_codes()


class ComputeResourceSerializer(BaseModelSerializer):
    gateway_server = serializers.CharField(required=False, max_length=255)

    class Meta:
        model = models.ComputeResource
        fields = "__all__"
        # not actually required for id since editable=False on model
        read_only_fields = ("id",)
        depth = 1
        error_status_codes = status_codes()


class PipelineSerializer(BaseModelSerializer):

    metadata = SchemalessJsonResponseSerializer(required=False)

    class Meta:
        model = models.Pipeline
        fields = "__all__"
        depth = 0
        error_status_codes = status_codes()


class JobSerializerBase(BaseModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    input_fileset_id = serializers.CharField(
        source="input_files",
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=24,
    )
    output_fileset_id = serializers.CharField(
        source="output_files",
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=24,
    )

    # params = serializers.JSONField(required=False)
    params = SchemalessJsonResponseSerializer(
        required=False
    )  # becomes OpenAPI 'object' type
    metadata = SchemalessJsonResponseSerializer(required=False)
    compute_resource = serializers.CharField(
        source="compute_resource.id",
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=24,
    )

    class Meta:
        model = models.Job
        fields = "__all__"
        # not actually required for id since editable=False on model
        read_only_fields = ("id",)
        depth = 0
        error_status_codes = status_codes()


class JobSerializerResponse(JobSerializerBase):
    input_fileset_id = serializers.CharField(
        source="input_files.id", max_length=24, default=""
    )
    output_fileset_id = serializers.CharField(
        source="output_files.id", max_length=24, default=""
    )
    # output_files = FileSerializer(many=True, required=False)

    class Meta:
        model = models.Job
        exclude = (
            "input_files",
            "output_files",
        )
        depth = 0
        error_status_codes = status_codes()

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = self._update_attrs(instance, validated_data)
        for field in getattr(self.Meta.model.ExtraMeta, "patchable_fields", []):
            if hasattr(instance, field):
                new_value = validated_data.get(field, getattr(instance, field))
                setattr(instance, field, new_value)
        instance.save()
        return instance


# TODO: modify this to trim down unnecessary output,
#       eg, we don't need the full nested sample_cart etc
class JobListSerializerResponse(JobSerializerResponse):
    latest_event = serializers.CharField(source="latest_event.event", default="")

    class Meta:
        model = models.Job
        exclude = ("input_files", "output_files")
        depth = 0
        error_status_codes = status_codes()


class JobListSerializerResponse_CSV(BaseModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        read_only=True,
        required=False,
        allow_null=True,
        default=serializers.CurrentUserDefault(),
    )
    owner_email = serializers.CharField(
        source="owner.email", allow_blank=True, allow_null=True
    )

    compute_resource_name = serializers.CharField(
        source="compute_resource.name",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    compute_resource = serializers.CharField(
        source="compute_resource.id",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    status = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # These might be genomics pipeline specific and need to change in the future
    pipeline_name = serializers.CharField(
        source="params.pipeline",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    pipeline_version = serializers.CharField(
        source="params.params.pipeline_version",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    genome = serializers.CharField(
        source="params.params.genome",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    user_genome_fasta_url = serializers.CharField(
        source="params.params.user_genome.fasta_url",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    user_genome_annotation_url = serializers.CharField(
        source="params.params.user_genome.annotation_url",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = models.Job
        fields = (
            "id",
            "created_time",
            "completed_time",
            "expiry_time",
            "owner_email",
            "owner",
            "pipeline_name",
            "pipeline_version",
            "genome",
            "user_genome_fasta_url",
            "user_genome_annotation_url",
            "status",
            "exit_code",
            "expired",
            "compute_resource",
            "compute_resource_name",
        )
        depth = 0
        error_status_codes = status_codes()


class JobSerializerRequest(JobSerializerBase):
    input_files = FileSerializer(many=True, required=False)

    class Meta(JobSerializerBase.Meta):
        depth = 1

    @transaction.atomic
    def create(self, validated_data):
        """

        :param validated_data:
        :type validated_data:
        :return:
        :rtype:
        """

        input_files_data = validated_data.pop("input_files", [])
        input_fileset_id = validated_data.pop("input_fileset_id", None)
        # Output files can only be updated in a PATCH operation
        # output_files_data = validated_data.pop('output_files', [])
        compute_resource_id = validated_data.pop("compute_resource", None)
        job = models.Job.objects.create(**validated_data)
        job = self._set_owner(job)

        if compute_resource_id:
            compute = models.ComputeResource.objects.get(id=compute_resource_id)
            job.compute_resource = compute

        # We create new file objects if the input file in the list has
        # details other than the id set. If only the id is set, we assume
        # it's an existing file and use that. If an input_fileset id is provided
        # we ignore anything in input_files and just use the specified FileSet.
        if not input_fileset_id:
            ifileset = job.input_files
            if not ifileset:
                ifileset = models.FileSet.objects.create(name="input", owner=job.owner)
            ifileset.name = f"Input files for job: {job.id}"
            for f in input_files_data:
                f_id = f.get("id", None)
                if not f_id:
                    input_file = models.File.objects.create(**f)
                else:
                    input_file = models.File.objects.get(id=f_id)

                ifileset.add(input_file)

            ifileset.save()
        else:
            if input_files_data:
                raise serializers.ValidationError(
                    "You should only specify an "
                    "input_fileset ID or a list "
                    "of input_files, not both."
                )
            ifileset = models.FileSet.objects.get(id=input_fileset_id)

        job.input_files = ifileset

        if not job.output_files:
            job.output_files = models.FileSet.objects.create(
                name=f"Output files for job: {job.id}", owner=job.owner
            )
            job.output_files.save()

        job.save()

        return job

    @transaction.atomic
    def update(self, instance, validated_data):
        serializer = JobSerializerRequest(instance, data=validated_data, partial=True)

        output_files_data = validated_data.pop("output_files", [])

        # status = validated_data.get('status', instance.status)

        ofiles = []
        for data in output_files_data:
            # We can add files by id if they exist, or create new files
            # from file objects (if id is left unset).
            file_id = data.get("id", None)
            if file_id is None:
                if "id" in data:
                    del data["id"]
                new_file = models.File.objects.create(**data)
                ofiles.append(new_file)
            else:
                # check the file_id actually exists before adding it
                existing_file = models.File.objects.get(id=file_id)
                ofiles.append(file_id)
            # ofile.save()

        instance.output_files.add(ofiles)
        # instance.save()  # instance.output_files.add saves

        return serializer.save()


class PipelineRunSerializer(BaseModelSerializer):

    owner = serializers.PrimaryKeyRelatedField(
        read_only=True,
        # default=serializers.CurrentUserDefault()
    )
    # job = serializers.PrimaryKeyRelatedField()

    sample_cart = SampleCartSerializer(required=False, allow_null=True)
    # sample_metadata = SchemalessJsonResponseSerializer(required=False)  # becomes OpenAPI 'object' type
    params = SchemalessJsonResponseSerializer(
        required=False
    )  # becomes OpenAPI 'object' type

    class Meta:
        model = models.PipelineRun
        fields = "__all__"
        read_only_fields = (
            "id",
            "owner",
        )
        depth = 1
        error_status_codes = status_codes()


# TODO: Should we convert File UUIDs from the associated SampleCart into URLs here ?
class PipelineRunCreateSerializer(PipelineRunSerializer):
    sample_cart = serializers.PrimaryKeyRelatedField(
        queryset=SampleCart.objects.all(), required=False, allow_null=True
    )
    # input_fileset = serializers.PrimaryKeyRelatedField(queryset=FileSet.objects.all())

    class Meta(PipelineRunSerializer.Meta):
        depth = 0

    def create(self, validated_data):
        run = models.PipelineRun.objects.create(**validated_data)
        self._set_owner(run)
        run.save()
        return run

    def update(self, instance, validated_data):
        # FIXME: This is not the right way to update the instance - we really should be
        # doing it via the serializer (as commented out below).
        # for k, v in validated_data.items():
        #     if k not in self.Meta.read_only_fields:
        #         setattr(instance, k, v)
        instance = self._update_attrs(instance, validated_data)
        instance.save()
        return instance

        # FIXME: This fails due to not validating the sample_cart primary key.
        #        Unclear why PrimaryKeyRelatedField isn't doing it's job
        # serializer = PipelineRunCreateSerializer(instance,
        #                                          data=validated_data)
        # if serializer.is_valid():
        #     return serializer.save()


class EventLogSerializer(BaseModelSerializer):
    extra = SchemalessJsonResponseSerializer(required=False)

    class Meta:
        model = models.EventLog
        fields = "__all__"
        read_only_fields = (
            "id",
            "user",
        )
        depth = 0
        error_status_codes = status_codes()

    def create(self, validated_data):
        obj = self.Meta.model.objects.create(**validated_data)
        obj.user = self.context.get("request").user
        obj.save()
        return obj


class JobEventLogSerializer(EventLogSerializer):
    class Meta:
        model = models.EventLog
        exclude = (
            "user",
            "timestamp",
            "object_id",
            "content_type",
        )
        read_only_fields = (
            "id",
            "user",
        )
        depth = 0
        error_status_codes = status_codes()


class FileListingItem(serializers.Serializer):
    name = serializers.CharField(required=True)
    location = serializers.URLField(required=True)
    type = serializers.CharField(required=True)
    tags = serializers.ListField(default=[])


class FileListing(serializers.Serializer):
    listing = FileListingItem(many=True)


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class RedirectResponseSerializer(serializers.Serializer):
    redirect = serializers.URLField(required=True)
    status = serializers.IntegerField(required=True)


class SocialAuthLoginRequest(serializers.Serializer):
    provider = serializers.CharField(required=True)
    code = serializers.CharField(required=True)
    clientId = serializers.CharField(required=True)
    redirectUri = serializers.URLField(required=True)


class SocialAuthLoginResponse(serializers.Serializer):
    id = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()


class UserProfileResponse(serializers.Serializer):
    id = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    full_name = serializers.CharField()
    email = serializers.CharField()
    profile_pic = serializers.URLField()

    # TODO: Determine if these tokens are used anywhere by clients (eg frontend / run_job.sh)
    #       and if not remove them from here. Out of scope for user profile and a potential
    #       security issue
    token = serializers.CharField()
    drf_token = serializers.CharField()
    jwt_authorization_header_prefix = serializers.CharField()
    drf_authorization_header_prefix = serializers.CharField()


class AccessTokenSerializer(BaseModelSerializer):
    content_type = serializers.CharField(required=True)
    object_id = serializers.CharField(required=True)

    class Meta:
        model = models.AccessToken
        fields = "__all__"
        read_only_fields = ("id", "created_by", "token")
        depth = 0
        error_status_codes = status_codes()

    def create(self, validated_data):
        target_id = validated_data["object_id"]
        target_content_type = validated_data["content_type"]
        target_obj = ContentType.objects.get(
            app_label="laxy_backend", model=target_content_type
        ).get_object_for_this_type(id=target_id)
        del validated_data["content_type"]
        del validated_data["object_id"]
        obj = self.Meta.model.objects.create(**validated_data)
        obj.created_by = getattr(self.context.get("request"), "user", None)
        obj.obj = target_obj
        obj.save()
        return obj


class JobAccessTokenRequestSerializer(AccessTokenSerializer):
    class Meta(AccessTokenSerializer.Meta):
        fields = (
            "id",
            "object_id",
            "content_type",
            "token",
            "created_by",
            "expiry_time",
            "created_time",
            "modified_time",
        )
        read_only_fields = (
            "id",
            "created_by",
            "token",
        )

    object_id = serializers.CharField(required=False)
    content_type = serializers.CharField(required=False)


class JobAccessTokenResponseSerializer(JobAccessTokenRequestSerializer):
    class Meta(JobAccessTokenRequestSerializer.Meta):
        fields = (
            "id",
            "object_id",
            "token",
            "created_by",
            "expiry_time",
            "created_time",
            "modified_time",
        )
        read_only_fields = (
            "id",
            "object_id",
            "created_by",
            "token",
            "object_id",
            "content_type",
        )
