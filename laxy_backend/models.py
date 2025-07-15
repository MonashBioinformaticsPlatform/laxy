import os
import socket
import typing
from typing import List, Sequence, Tuple, Union, AnyStr, Iterable
import collections
from collections import OrderedDict
from datetime import datetime, timedelta
import math
import json
import csv
from pathlib import Path
from urllib.parse import urlparse
import base64
from uuid import uuid4
from io import StringIO, BytesIO, BufferedRandom

import backoff
from django.db.utils import IntegrityError
import pandas as pd
import paramiko
from paramiko import SSHClient, ssh_exception, RSAKey, AutoAddPolicy
from jsonschema import validate
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

from django.conf import settings
from django.utils import timezone
from django.db import models, transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.db.models.constraints import UniqueConstraint
from django.db.models import Q
from django.dispatch import receiver
from django.core.handlers.wsgi import WSGIRequest
from django.core.files.storage import get_storage_class, Storage
from django.core.serializers import serialize
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import (
    Model,
    Manager,
    CharField,
    URLField,
    ForeignKey,
    BooleanField,
    IntegerField,
    DateTimeField,
    QuerySet,
)
from django.contrib.postgres.fields import ArrayField

# from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from guardian.mixins import GuardianUserMixin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import reversion
from rest_framework.authtoken.models import Token
from storages.backends.sftpstorage import SFTPStorage, SFTPStorageFile

from .tasks import orchestration
from .util import (
    unique,
    has_method,
    generate_uuid,
    generate_secret_key,
    find_filename_and_size_from_url,
    laxy_sftp_url,
    generate_cluster_stack_name,
)

import logging

logger = logging.getLogger(__name__)

if "postgres" not in settings.DATABASES["default"]["ENGINE"]:
    from jsonfield import JSONField
else:
    from django.contrib.postgres.fields import JSONField

SCHEME_STORAGE_CLASS_MAPPING = {
    "file": "django.core.files.storage.FileSystemStorage",
    "sftp": "storages.backends.sftpstorage.SFTPStorage",
    "laxy+sftp": "storages.backends.sftpstorage.SFTPStorage",
}
"""
Maps URL schemes to Django storage backends that can handle them.
"""

CACHE_SFTP_CONNECTIONS = True
"""
If True, use CACHED_SFTP_STORAGE_CLASS_INSTANCES to cache SFTPStorage classes
to allow connection pooling to the same ComputeResource.

Seems buggy, so disabled by default.
"""

CACHED_SFTP_STORAGE_CLASS_INSTANCES = {}
"""
Cached instances on the SFTPStorage class, keyed by ComputeResource.id to allow 
connection pooling for SFTP access to the same host.
"""


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Automatically create an Django Rest Framework API Token for every user when
    their User model is first created.

    http://www.django-rest-framework.org/api-guide/authentication/#generating-tokens
    """
    if created:
        Token.objects.create(user=instance)


class URIValidator(URLValidator):
    """
    A validator for generic URIs that also allows additional schemes not
    supported by the default Django URLValidator.
    """

    schemes = (
        "http",
        "https",
        "ftp",
        "sftp",
        "laxy+sftp",
        "s3",
        "magnet",
        "file",
    )

    def __call__(self, value):
        try:
            scheme = urlparse(value).scheme
            # skip additional validation of file, magnet, s3 etc
            # since the regexes used in URLValidator assumes web addresses
            # with hosts/IPs etc
            if scheme not in super().schemes:
                return
        except ValueError as e:
            raise ValidationError(self.message, code=self.code)
        super().__call__(value)


class ExtendedURIField(URLField):
    default_validators = [URIValidator()]


class Timestamped(Model):
    class Meta:
        abstract = True
        get_latest_by = ["-modified_time"]

    created_time = DateTimeField(auto_now_add=True)
    modified_time = DateTimeField(auto_now=True)


def _job_expiry_datetime():
    job_ttl = getattr(settings, "JOB_EXPIRY_TTL_DEFAULT", 30 * 24 * 60 * 60)
    return timezone.now() + timedelta(seconds=job_ttl)


class Expires(Model):
    class Meta:
        abstract = True
        get_latest_by = ["-expiry_time"]

    expiry_time = DateTimeField(blank=True, null=True, default=_job_expiry_datetime)
    expired = BooleanField(default=False)


class ReadOnlyFlag(Model):
    """
    Mixin that adds a readonly boolean to a model.
    Model will not save/delete when this flag is True (on the instance).

    Setting the readonly flag has the side effect of saving the current instance (but updates ONLY
    the _readonly field on the database, ignoring other modified fields).

    Beware: custom model Managers, raw SQL and bulk operations may not always prevented from modifying
    the model if they bypass the model instance-level save/delete. The _readonly database field can be
    modified directly - this mixin isn't intended to completed lock a row, just act as a convenient
    pattern to help in typical usage.

    (If making a row readonly really really matters, you might want to do something like:
     https://www.postgresql.org/docs/9.5/ddl-rowsecurity.html).

    eg intended usage:

    >>> class MyReadonlyModel(ReadOnlyFlag, Model):
    >>>     pass

    >>> myreadonlymodel.readonly = False
    >>> myreadonlymodel.save()  # works fine
    >>> myreadonlymodel.readonly = True
    >>> myreadonlymodel.save()
    RuntimeError: Attempting to save readonly model: 1

    """

    class Meta:
        abstract = True

    _readonly = BooleanField(default=False)

    @property
    def readonly(self):
        return self._readonly

    @readonly.setter
    def readonly(self, state):
        if state != self._readonly:
            self._readonly = state
            super(ReadOnlyFlag, self).save(update_fields=["_readonly"])

    def save(self, *args, **kwargs):
        if self.readonly:
            raise RuntimeError(f"Attempting to save readonly model: {self.id}")
        super(ReadOnlyFlag, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.readonly:
            raise RuntimeError(f"Attempting to delete readonly model: {self.id}")
        super(ReadOnlyFlag, self).delete(*args, **kwargs)


class UUIDModel(Model):
    # We don't use the native UUIDField (even though it's more efficient on
    # Postgres) since it makes inspecting the database for the job_id a
    # nuisance.
    # id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Alternative: https://github.com/nebstrebor/django-shortuuidfield ?

    # IDEA: If we were to make this NOT abstract and subclass it for various models,
    # we get one big table where we can query UUIDModel.objects.get(id=uuid) to get
    # any of our objects by UUID (Currently won't work due to related_name
    # backreference clashes, but these could be resolved).
    # https://docs.djangoproject.com/en/2.0/topics/db/models/#multi-table-inheritance
    class Meta:
        abstract = True

    id = CharField(
        primary_key=True, editable=False, max_length=24, default=generate_uuid
    )

    def uuid(self):
        return self.id

    def __unicode__(self):
        return self.id


class User(AbstractUser, UUIDModel, GuardianUserMixin):
    pass


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        primary_key=True,
        on_delete=models.CASCADE,
        blank=False,
        related_name="profile",
    )
    image_url = models.URLField(max_length=2048, blank=True, null=True)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created or not UserProfile.objects.filter(user=instance).exists():
        UserProfile.objects.create(user=instance)
    instance.profile.save()


class JSONSerializable:
    def to_json(self):
        return serialize("json", self)


# class JobParams(JSONSerializable, UUIDModel):
#     """
#     This class exists as a parent for all pipeline run models (eg JobParams),
#     to allow a Job to point to a generic parameter model via a ForeignKey
#     (Job->JobParams).
#
#     The intention is that as other specific parameter subclasses are created
#     (eg ChipSeqPipelineRun, HomologyModellingPipelineRun), we can retrieve them
#     via Job.params.
#
#     All JobParams subclasses should be JSON serializable (via implementing .to_json())
#     such that we can get the JSON representation without knowing the specific type.
#
#     We can also retrieve any run parameter set via it's UUID without knowing it's
#     specific type via JobParams.object.get(id=some_params_id).to_json()
#
#     https://docs.djangoproject.com/en/2.0/topics/db/models/#multi-table-inheritance
#     """
#     pass


class EventLog(UUIDModel):
    class Meta:
        ordering = ["-timestamp"]
        get_latest_by = ["timestamp"]

    user = ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="event_logs",
    )
    timestamp = DateTimeField(default=timezone.now, db_index=True)
    event = CharField(max_length=64)
    message = CharField(max_length=256, blank=True, null=True)
    extra = JSONField(default=OrderedDict)

    content_type = ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    object_id = CharField(null=True, max_length=24, db_index=True)
    obj = GenericForeignKey("content_type", "object_id")

    @staticmethod
    def log(event, message="", user=None, extra=None, obj=None, timestamp=None):
        if extra is None:
            extra = {}
        content_type = None
        object_id = None
        if obj is not None:
            content_type = ContentType.objects.get_for_model(obj)
            object_id = obj.pk
        if timestamp is None:
            timestamp = timezone.now()

        event = EventLog.objects.create(
            user=user,
            event=event,
            message=message,
            extra=extra,
            content_type=content_type,
            object_id=object_id,
            timestamp=timestamp,
        )
        return event


class Pipeline(Timestamped, UUIDModel):
    """
    A record for a pipeline that may be available to run.
    """

    class Meta:
        permissions = (("run_pipeline", "Can run this pipeline"),)

    owner = ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="pipelines",
    )
    name = CharField(max_length=256)
    public = BooleanField(default=False)

    # Contains extra pipeline info like:
    #    {"versions": ["1.5.3", "1.5.4"]}
    # Ideally we should keep the data here independent
    # of platform specific details (eg shouldn't be specific
    # to a particular ComputeResource).
    metadata = JSONField(default=OrderedDict)

    def allowed_to_run(self, user: User):
        return user.has_perm("laxy_backend.run_pipeline", self)


class SystemStatus(Timestamped, UUIDModel):
    """
    A system status message to be displayed to the user, like a MOTD banner
    (eg under conditions where there may be a compute backend outage).
    """

    message = CharField(max_length=256, blank=True, null=True)
    long_message = CharField(max_length=2048, blank=True, null=True)
    link_url = ExtendedURIField(max_length=2048, blank=True, null=True)
    status = CharField(max_length=32, default="online")
    active = BooleanField(default=False)
    start_time = DateTimeField(blank=True, null=True)  # becomes shown after this time
    end_time = DateTimeField(blank=True, null=True)  # not shown after this time
    # if two SystemStatus messages are active together, highest priority wins
    priority = IntegerField(default=0)


class ComputeResourceDecommissioned(Exception):
    pass


@reversion.register()
class ComputeResource(Timestamped, UUIDModel):
    # model created, no actual resource yet
    STATUS_CREATED = "created"
    # actual resource is being created
    STATUS_STARTING = "starting"
    # resource is online and functioning as expected
    STATUS_ONLINE = "online"
    # resource isn't functioning correctly. may be temporary.
    STATUS_ERROR = "error"
    # resource is intentionally offline and shouldn't be used. may be temporary.
    STATUS_OFFLINE = "offline"
    # resource is being decommissioned and shouldn't be used. permanent.
    STATUS_TERMINATING = "terminating"
    # resource has been decommissioned and won't be available. permanent.
    STATUS_DECOMMISSIONED = "decommissioned"

    COMPUTE_STATUS_CHOICES = (
        (STATUS_CREATED, "object_created"),
        (STATUS_STARTING, "starting"),
        (STATUS_ONLINE, "online"),
        (STATUS_ERROR, "error"),
        (STATUS_OFFLINE, "offline"),
        (STATUS_TERMINATING, "terminating"),
        (STATUS_DECOMMISSIONED, "decommissioned"),
    )

    owner = ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="compute_resources",
    )
    status = CharField(
        max_length=64, choices=COMPUTE_STATUS_CHOICES, default=STATUS_CREATED
    )

    host = CharField(max_length=255, blank=True, null=True)
    gateway_server = CharField(max_length=255, blank=True, null=True)
    disposable = BooleanField(default=False)
    name = CharField(max_length=128, blank=True, null=True)
    priority = IntegerField(default=0)
    archive_host = ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="source_host",
    )

    extra = JSONField(default=OrderedDict)
    """
    This contains resource type specific data. For a typical SSH-accessible 
    ComputeResource, it will contain a base_dir, username, private_key, queue_type 
    and possibly other configuration values.
    
    See views.ComputeResourceCreate.post docs for details.
    """

    def __str__(self):
        return f"{self.name} ({self.id})"

    @classmethod
    def get_best_available(cls):
        return (
            cls.objects.filter(status=cls.STATUS_ONLINE).order_by("-priority").first()
        )

    @property
    def sftp_storage(self) -> Union[SFTPStorage, None]:
        @backoff.on_exception(
            backoff.expo, (socket.gaierror,), max_tries=3, jitter=backoff.full_jitter
        )
        def _connect(_storage_instance: SFTPStorage):
            """
            Attempt to connect to SFTP server, with retries.
            """
            # Accessing the .sftp property ensures the connection is still open, reopens it if it's not
            _ = _storage_instance.sftp

        if not self.available:
            msg = f"Cannot access storage for ComputeResource {self.id} - status='{self.status}'"
            if self.status == ComputeResource.STATUS_DECOMMISSIONED:
                raise ComputeResourceDecommissioned(msg)
            raise Exception(msg)

        if CACHE_SFTP_CONNECTIONS:
            _storage_instance: SFTPStorage = CACHED_SFTP_STORAGE_CLASS_INSTANCES.get(
                self.id, None
            )
            if (
                _storage_instance is not None
                and _storage_instance._ssh.get_transport() is not None
            ):
                if _storage_instance._ssh.get_transport().is_active():
                    # This ensures connection is still open, reopens it if it's not
                    _connect(_storage_instance)
                    return _storage_instance
                else:
                    _storage_instance.sftp.close()

        storage_class = get_storage_class(
            SCHEME_STORAGE_CLASS_MAPPING.get("laxy+sftp", None)
        )

        host = self.hostname
        port = self.port
        private_key = self.private_key
        username = self.extra.get("username")
        params = dict(
            port=port,
            username=username,
            pkey=RSAKey.from_private_key(StringIO(private_key)),
        )
        # storage = SFTPStorage(host=host, params=params)
        storage: SFTPStorage = storage_class(host=host, params=params)
        _connect(
            storage
        )  # Do this to ensure we can connect before caching the SFTPStorage class
        CACHED_SFTP_STORAGE_CLASS_INSTANCES[self.id] = storage

        return storage

    def ssh_client(self, *args, **kwargs) -> paramiko.SSHClient:
        """
        Return an SSHClient instance connected to the ComputeResource.

        eg.
        with compute_resource.ssh_client() as client:
            stdin, stdout, stderr = client.exec_command('ls')

        Be sure to use 'with' so the context manager can close the connection when
        you are finished with the client.

        :return: A paramiko SSHClient instance connected to the compute resource.
        :rtype: paramiko.SSHClient
        """
        remote_username = self.extra.get("username", "laxy")

        # TODO: Cache connections to the same ComputeResource
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy)
        # client.load_system_host_keys()
        client.connect(
            self.hostname,
            port=self.port,
            username=remote_username,
            pkey=RSAKey.from_private_key(StringIO(self.private_key)),
            **kwargs,
        )

        return client

    def running_jobs(self):
        """
        Returns a Django QuerySet of all the jobs currently running or
        on this compute resource.

        :return: The pending Jobs
        :rtype: django.db.models.query.QuerySet
        """
        return Job.objects.filter(compute_resource=self, status=Job.STATUS_RUNNING)

    def pending_jobs(self):
        """
        Returns a Django QuerySet of all the jobs currently running or
        waiting to run on this compute resource.

        :return: The pending Jobs
        :rtype: django.db.models.query.QuerySet
        """
        return Job.objects.filter(
            compute_resource=self,
            status__in=[Job.STATUS_CREATED, Job.STATUS_RUNNING, Job.STATUS_STARTING],
        )

    def dispose(self):
        """
        Terminates the ComputeResource such that it can no longer be used.
        eg, may permanently terminate the associated AWS instance.

        Returns False if resource isn't disposable.

        :return:
        :rtype:
        """
        if self.disposable:
            orchestration.dispose_compute_resource.apply_async(
                args=({"compute_resource_id": self.id},)
            )
        else:
            return False

    @property
    def available(self):
        return self.status == ComputeResource.STATUS_ONLINE

    @property
    def private_key(self):
        return base64.b64decode(self.extra.get("private_key")).decode("ascii")

    @property
    def hostname(self):
        return self.host.split(":")[0]

    @property
    def port(self) -> int:
        """
        Return the port associated with the host, as a int.

        :return: The port (eg 22)
        :rtype: int
        """
        if ":" in self.host:
            return int(self.host.split(":").pop())
        else:
            return "22"

    @property
    def jobs_dir(self) -> str:
        """
        Return the base path for job storage on the host, eg /scratch/jobs/

        :return: The path where jobs are stored on the ComputeResource.
        :rtype: str
        """
        fallback_base_dir = getattr(settings, "DEFAULT_JOB_BASE_PATH", "/tmp")
        return self.extra.get("base_dir", fallback_base_dir)

    @property
    def queue_type(self):
        return self.extra.get("queue_type", None)

    @queue_type.setter
    def queue_type(self, queue_type: str):
        self.extra["queue_type"] = queue_type
        self.save()


@reversion.register()
class Job(Expires, Timestamped, UUIDModel):
    JOB_PARAMS_SCHEMA = {
        "type": "object",
        "properties": {
            "pipeline": {
                "type": "string",
                "description": "The name of the pipeline to run.",
                # Basic slug-like pattern, no slashes or dots.
                "pattern": "^[a-zA-Z0-9_-]+$"
            },
            "params": {
                "type": "object",
                "properties": {
                    "pipeline_version": {
                        "type": "string",
                        "description": "The version of the pipeline.",
                        # Allow dots and hyphens for version strings.
                        "pattern": "^[a-zA-Z0-9_.-]+$"
                    }
                },
                "additionalProperties": True
            },
            "job_template_overrides": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": [],
        "additionalProperties": True
    }

    class ExtraMeta:
        patchable_fields = ["params", "metadata"]

    """
    Represents a processing job (typically a long running remote job managed
    by a Celery task queue).
    """
    STATUS_CREATED = "created"
    STATUS_HOLD = "hold"
    STATUS_STARTING = "starting"
    STATUS_RUNNING = "running"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETE = "complete"

    JOB_STATUS_CHOICES = (
        (STATUS_CREATED, "object_created"),
        (STATUS_HOLD, "hold"),
        (STATUS_STARTING, "starting"),
        (STATUS_RUNNING, "running"),
        (STATUS_FAILED, "failed"),
        (STATUS_CANCELLED, "cancelled"),
        (STATUS_COMPLETE, "complete"),
    )

    owner = ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, related_name="jobs"
    )

    status = CharField(
        max_length=64, choices=JOB_STATUS_CHOICES, default=STATUS_CREATED
    )
    exit_code = IntegerField(blank=True, null=True)
    remote_id = CharField(max_length=64, blank=True, null=True)

    # jsonfield or native Postgres
    # params = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})

    # django-jsonfield or native Postgres
    params = JSONField(default=OrderedDict)

    # Intended for non-parameter metadata about the job
    # - eg, post-run extracted results that might be used in the web frontend
    # (eg {"results": {"predicted-strandedness": "forward", "strand-bias": 0.98}} )
    metadata = JSONField(default=OrderedDict)

    # A JSON-serializable params class that may be specialized via
    # multiple-table inheritance
    # params = ForeignKey(JobParams,
    #                     blank=True,
    #                     null=True,
    #                     on_delete=models.SET_NULL)

    input_files = ForeignKey(
        "FileSet",
        null=True,
        blank=True,
        related_name="jobs_as_input",
        on_delete=models.SET_NULL,
    )
    output_files = ForeignKey(
        "FileSet",
        null=True,
        blank=True,
        related_name="jobs_as_output",
        on_delete=models.SET_NULL,
    )

    compute_resource = ForeignKey(
        ComputeResource,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="jobs",
    )

    completed_time = DateTimeField(blank=True, null=True)

    @transaction.atomic()
    def _init_filesets(self, save=True):
        if not self.input_files:
            self.input_files = FileSet(
                name=f"Input files for job: {self.id}", path="input", owner=self.owner
            )
            if save:
                self.input_files.save()

        if not self.output_files:
            self.output_files = FileSet(
                name=f"Output files for job: {self.id}", path="output", owner=self.owner
            )
            if save:
                self.output_files.save()

    def save(self, *args, **kwargs):
        super(Job, self).save(*args, **kwargs)

        # For a single-use ('disposable') ComputeResource associated with a
        # single job, we automatically name the resource based on the associated
        # job UUID.
        compute = self.compute_resource
        if compute and compute.disposable and not compute.name:
            compute.name = generate_cluster_stack_name(self)
            compute.save()

    def events(self):
        return EventLog.objects.filter(object_id=self.id)

    def log_event(self, event_type: str, message: str, extra=None) -> EventLog:
        if extra is None:
            extra = {}

        eventlog = EventLog(
            event=event_type,
            message=message,
            extra=extra,
            user=self.owner,
            object_id=self.id,
            content_type=ContentType.objects.get_for_model(self),
        )
        eventlog.save()
        return eventlog

    def latest_event(self):
        try:
            return (
                EventLog.objects.filter(object_id=self.id)
                .exclude(event__exact="JOB_STATUS_CHANGED")
                .latest()
            )
        except EventLog.DoesNotExist:
            return EventLog.objects.none()

    def get_files(self) -> models.query.QuerySet:
        # Combine querysets
        return self.input_files.get_files() | self.output_files.get_files()

    @property
    def abs_path_on_compute(self):
        """
        DEPRECATED: Use job_path_on_compute directly (or rename this property to
        something less confusing, given that Job.compute_resource is where the Job ran,
        not where the files currently reside)

        Returns the absolute path to the job directory on it's ComputeResource.
        SSH-centric, but might map to other methods of accessing storage.

        :return: An absolute path to the job directory.
        :rtype: str
        """
        return job_path_on_compute(self, self.compute_resource)

    @property
    def done(self):
        """
        Returns True if the job has finished, either successfully
        or unsuccessfully.

        :return: True if job is no longer running.
        :rtype: bool
        """
        return (
            self.status == Job.STATUS_COMPLETE
            or self.status == Job.STATUS_CANCELLED
            or self.status == Job.STATUS_FAILED
        )

    @transaction.atomic()
    def add_files_from_tsv(self, tsv_table: Union[List[dict], str, bytes], save=True):
        """
        Works with TSV and CSV, due to use of pd.read_table(sep=None)

        ```tsv
        filepath	checksum	type_tags	metadata
        input/some_dir/table.txt	md5:7d9960c77b363e2c2f41b77733cf57d4	text,csv,google-sheets	{}
        input/some_dir/sample1_R2.fastq.gz	md5:d0cfb796d371b0182cd39d589b1c1ce3	fastq	{}
        input/some_dir/sample2_R2.fastq.gz	md5:a97e04b6d1a0be20fcd77ba164b1206f	fastq	{}
        output/sample2/alignments/sample2.bam	md5:7c9f22c433ae679f0d82b12b9a71f5d3	bam,alignment,bam.sorted,jbrowse	{}
        output/sample2/alignments/sample2.bai	md5:e57ea180602b69ab03605dad86166fa7	bai,jbrowse	{}
        ```

        ..or a version with a location column ..

        ```tsv
        location    filepath	checksum	type_tags	metadata
        laxy+sftp://BlA4F00/Vl4F1U/input/some_dir/table.txt input/some_dir/table.txt	md5:7d9960c77b363e2c2f41b77733cf57d4	text,csv,google-sheets	{}
        laxy+sftp://BlA4F00/Vl4F1U/input/some_dir/sample1_R2.fastq.gz   input/some_dir/sample1_R2.fastq.gz	md5:d0cfb796d371b0182cd39d589b1c1ce3	fastq	{}
        laxy+sftp://BlA4F00/Vl4F1U/input/some_dir/sample2_R2.fastq.gz   input/some_dir/sample2_R2.fastq.gz	md5:a97e04b6d1a0be20fcd77ba164b1206f	fastq	{}
        laxy+sftp://BlA4F00/Vl4F1U/output/sample2/alignments/sample2.bam    output/sample2/alignments/sample2.bam	md5:7c9f22c433ae679f0d82b12b9a71f5d3	bam,alignment,bam.sorted,jbrowse	{}
        laxy+sftp://BlA4F00/Vl4F1U/output/sample2/alignments/sample2.bai    output/sample2/alignments/sample2.bai	md5:e57ea180602b69ab03605dad86166fa7	bai,jbrowse	{}
        ```

        :param tsv_table:
        :type tsv_table:
        :param save:
        :type save:
        :return:
        :rtype:
        """
        from laxy_backend.serializers import FileBulkRegisterSerializer

        if isinstance(tsv_table, str) or isinstance(tsv_table, bytes):
            table = json.loads(
                pd.read_table(BytesIO(tsv_table), sep=None, engine="python").to_json(
                    orient="records"
                )
            )
        elif isinstance(tsv_table, list):
            table = tsv_table
        else:
            raise ValueError("tsv_table must be str, bytes or a list of dicts")

        in_files = []
        out_files = []

        self._init_filesets()

        for row in table:
            # When a pd.DataFrame is converted to JSON (.to_json()), values than
            # contain JSON strings are not converted to nested JSON objects.
            # So we do this manually for the metadata field.
            if row.get("metadata", None):
                row["metadata"] = json.loads(row["metadata"])

            f = FileBulkRegisterSerializer(data=row)
            if f.is_valid(raise_exception=True):

                # Check if file exists by path in input/output filesets already,
                # if so, update existing file
                fpath = f.validated_data["path"]
                fname = f.validated_data["name"]
                existing = self.get_files().filter(name=fname, path=fpath).first()
                if existing:
                    f = FileBulkRegisterSerializer(existing, data=row, partial=True)
                    f.is_valid(raise_exception=True)
                    f_obj = f.instance

                if not existing:
                    f_obj = f.create(f.validated_data)

                f_obj.owner = self.owner
                if not f_obj.location and self.compute_resource is not None:
                    location = laxy_sftp_url(self, path=f"{f_obj.path}/{f_obj.name}")
                    f_obj.location = location
                if save:
                    f_obj = f.save()

            pathbits = Path(f.validated_data.get("path", "").strip("/")).parts
            if pathbits and pathbits[0] == "input":
                self.input_files.add(f_obj)
                in_files.append(f_obj)

            elif pathbits and pathbits[0] == "output":
                self.output_files.add(f_obj)
                out_files.append(f_obj)

            else:
                logger.debug(
                    f"Not adding file {f_obj.full_path} ({f_obj.id}) "
                    f"- File paths for a Job must begin with input/ or output/"
                )
                # raise ValueError("File paths for a Job must begin with input/ or output/")

        return in_files, out_files


# Alternatives to a pre_save signal here might be using:
# https://github.com/kajic/django-model-changes which gives a more streamlined
# way of watching fields via pre/post_save signals
# or using properties on the model:
# https://www.stavros.io/posts/how-replace-django-model-field-property/
@receiver(pre_save, sender=Job)
def update_job_completed_time(sender, instance, raw, using, update_fields, **kwargs):
    """
    Takes actions every time a Job is saved, so changes to certain fields
    can have side effects (eg automatically setting completion time).
    """
    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass
    else:
        if instance.done and not obj.done and not obj.completed_time:
            instance.completed_time = timezone.now()


@receiver(pre_save, sender=Job)
def job_status_changed_event_log(sender, instance, raw, using, update_fields, **kwargs):
    """
    Creates an event log entry every time a Job is saved with a changed status.
    """
    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass
    else:
        if instance.status != obj.status:
            EventLog.log(
                "JOB_STATUS_CHANGED",
                message=f"Job status changed: {obj.status} → {instance.status}",
                user=instance.owner,
                obj=obj,
                extra=OrderedDict({"from": obj.status, "to": instance.status}),
            )


@receiver(pre_save, sender=Job)
def job_init_filesets(sender, instance: Job, raw, using, update_fields, **kwargs):
    if instance.pk is None:
        instance._init_filesets(save=False)


@receiver(pre_save, sender=Job)
def sanitize_job_params(sender, instance: Job, raw, using, update_fields, **kwargs):
    """
    Validates job parameters against a JSON schema to ensure structure and
    prevent unsafe values that could be used in path construction.
    """
    if instance.params:
        try:
            validate(instance=instance.params, schema=Job.JOB_PARAMS_SCHEMA)
        except JSONSchemaValidationError as e:
            # Raising a Django ValidationError is more idiomatic here
            # and will be handled nicely by serializers and forms.
            raise DjangoValidationError(
                {'params': f"Job.params failed validation: {e.message}"}
            ) from e


@receiver(post_save, sender=Job)
def new_job_event_log(sender, instance, created, raw, using, update_fields, **kwargs):
    if created and not raw:
        EventLog.log(
            "JOB_STATUS_CHANGED",
            message="Job created.",
            user=instance.owner,
            obj=instance,
            extra={"from": None, "to": instance.status},
        )


@reversion.register()
class FileLocation(UUIDModel):
    class Meta:
        unique_together = (
            "url",
            "file",
        )

        # indexes = [
        #     models.Index(fields=["file", "default"]),
        # ]

    # The URL to the file. Could be file://, https://, s3://, sftp://
    url = ExtendedURIField(max_length=2048, blank=False, null=False)
    file = ForeignKey(
        "File",
        related_name="locations",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
    )
    default = BooleanField(blank=False, null=False, default=False)

    def __str__(self):
        return self.url

    # TODO: For URLs that require some kind of authentication, we could
    #       store eg, Authorization: header values here. Alternatively,
    #       this might be a ForeignKey that can point to an AuthCreds object
    #       (more efficient in the case where many FileLocations will use
    #       exactly the same authentication values)
    # authentication = JSONField(default=OrderedDict)

    def set_as_default(self, save=True) -> "QuerySet[FileLocation]":
        """
        Set this FileLocation record as the 'default', ensuring all others
        are set to default=False.

        :param save: Automatically save modified objects.
        :type save: bool
        :return: A queryset of all FileLocations for this file. If using
                  save=False, you can explicitly .save() the objects returned
                  here.
        :rtype: QuerySet[FileLocation]
        """
        with transaction.atomic():
            for f in self.file.locations.exclude(id=self.id):
                f.default = False
                if save:
                    f.save()
            self.default = True
            if save:
                self.save()

        return self.file.locations

    @property
    def path_on_compute(self):
        """
        Return the ComputeResource encoded in a URL, if possible.

        :return: The ComputeResource object.
        :rtype: laxy_backend.models.ComputeResource
        """
        compute = get_compute_resource_for_location(self.url)
        if compute is None:
            return None

        url = urlparse(self.url)
        base_dir = compute.extra.get(
            "base_dir", getattr(settings, "DEFAULT_JOB_BASE_PATH")
        )
        file_path = str(Path(base_dir) / Path(url.path).relative_to("/"))
        return file_path


@receiver(post_delete, sender=FileLocation)
def ensure_one_default_filelocation(
    sender: typing.Type[FileLocation], instance: FileLocation, using, **kwargs
):
    # Ensure that we always have a default FileLocation after deleting
    if not instance.file.locations.filter(default=True).exists():
        firstloc = instance.file.locations.first()
        if firstloc is not None:
            firstloc.set_as_default()


def get_compute_resource_str_for_location(
    location: Union[str, FileLocation]
) -> Union[str, None]:

    location = str(location)

    url = urlparse(location)
    scheme = url.scheme
    if scheme != "laxy+sftp":
        return None
    if "." in url.netloc:
        return None
    # use netloc not hostname, since hostname forces lowercase
    return url.netloc


def get_compute_resource_for_location(
    location: Union[str, FileLocation]
) -> Union[ComputeResource, None]:

    compute_id = get_compute_resource_str_for_location(location)
    try:
        compute = ComputeResource.objects.get(id=compute_id)
    except ComputeResource.DoesNotExist as e:
        raise e

    return compute


def get_storage_class_for_location(
    location: Union[str, FileLocation]
) -> Union[Storage, None]:
    if isinstance(location, FileLocation):
        location = location.url

    url = urlparse(location)
    scheme = url.scheme
    if scheme == "laxy+sftp":
        compute = get_compute_resource_for_location(location)
        if compute is None:
            raise Exception(f"Cannot extract ComputeResource ID from: {location}")

        return compute.sftp_storage

    # TODO: This needs to be carefully reworked or removed. The intention would be to refer to a mountpoint
    #       relative to the Laxy backend server filesystem (eg an NFS mount), however there is scope for
    #       reading arbitrary files on the server if implemented incorrectly.
    elif scheme == "file":
        # raise NotImplementedError('file:// URLs are currently not supported')
        # TODO: location defaults to Djangos MEDIA_ROOT setting. If we were to use mount points local to the
        # backend filesystem, we need a mechanism to set this location (eg to something equivalent to
        # `base_dir` in the ComputeResource extra params. Setting location to something like
        # `/scratch/jobs/{job_id}/` per-job should mitigate some of the risk here (assuming Django's
        # FileSystemStorage doesn't allow relative/paths/like/../../../this/ outside the base location.
        storage_class = get_storage_class(
            SCHEME_STORAGE_CLASS_MAPPING.get(scheme, None)
        )
        return storage_class(location="/")
    else:
        raise NotImplementedError(
            f"Unsupported scheme or storage backend for file location: {location}"
        )
        # return None


def job_path_on_compute(job: Union[str, Job], compute: ComputeResource) -> str:
    """
    Given a Job (or job ID) and a ComputeResource, return the absolute path to
    that Job on that host.

    :param job: A Job or job ID
    :type job: Union[str, Job]
    :param compute: The ComputeResource
    :type compute: ComputeResource
    :return: The absolute path to the Job directoty on the ComputeResource
    :rtype: str
    """
    if isinstance(job, Job):
        job = job.id

    return os.path.normpath(os.path.join(compute.jobs_dir, job))


@reversion.register()
class File(Timestamped, UUIDModel):
    class Meta:
        indexes = [
            models.Index(fields=["path", "name"]),
            models.Index(fields=["fileset", "path", "name"]),
        ]

        # A fileset must only have one file record with a given path+name
        # Files outside a fileset don't need unique path+name
        constraints = [
            UniqueConstraint(
                fields=["fileset", "path", "name"],
                condition=Q(fileset__isnull=False),
                name="unique_file",
            ),
        ]

    class ExtraMeta:
        patchable_fields = ["metadata"]

    """
    File model.
    """
    # The filename, as might be used on a POSIX filesystem.
    # Longest filename on most Linux filesystems is 255, hence max_length.
    # Often equivalent to path.basename(location), but not always.
    name = CharField(max_length=255, blank=True, null=True)

    # We store the file path (minus the filename) since the location URL won't
    # always contain it (eg shortened links). Longest path on most Linux
    # filesystems is 4096, hence max_length.
    path = CharField(max_length=4096, blank=True, null=True)

    # Any hash supported by hashlib, and xxhash, in the format:
    # hashtype:th3actualh4shits3lf
    # eg: md5:11fca9c1f654078189ad040b1132654c
    checksum = CharField(max_length=255, blank=True, null=True)
    # owner and fileset use on_delete=models.SET_NULL rather than CASCADE,
    # since we don't want to lose reference to files-on-disk, which will
    # need to be deleted/moved by an async (eg celery) deletion task.
    owner = ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True, related_name="files"
    )

    fileset = ForeignKey(
        "FileSet", related_name="files", null=True, on_delete=models.SET_NULL
    )

    type_tags = ArrayField(
        models.CharField(max_length=255), default=list, null=True, blank=True
    )

    deleted_time = DateTimeField(blank=True, null=True)

    # Arbitrary metadata.
    metadata = JSONField(default=OrderedDict)

    # metadata = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})

    # This stores the location string (URL) when it's updated on the instance, prior to saving
    _dirty_location: Union[str, None] = None

    # There is no direct link from File->Job, instead we use FileSet->Job.
    # This way, Files represent a single unique file (on disk, or at a URL),
    # and FileSets can represent a set of files used
    # as input/output of a Job.
    # job = ForeignKey(Job,
    #                  on_delete=models.CASCADE,
    #                  related_name='files')

    def save(self, *args, **kwargs):
        if self._dirty_location is not None:
            with transaction.atomic():
                fileloc = self.locations.filter(url=self._dirty_location).first()
                if fileloc is None:
                    # Catch the case where the File doesn't exist yet, ensure it's
                    # created so that FileLocation.file ForeignKey constraint is satisfied
                    super().save(*args, **kwargs)
                    fileloc = FileLocation(url=self._dirty_location, file=self)

                fileloc.set_as_default(save=True)
                self._dirty_location = None
        else:
            super().save(*args, **kwargs)

    @property
    def location(self):
        if self._dirty_location is not None:
            return self._dirty_location

        fileloc = self.locations.filter(default=True).first()
        if fileloc:
            return fileloc.url

        return None

    @location.setter
    def location(self, url):
        self._dirty_location = url

        # If the instance is being created
        if self._state.adding:
            if not self.name:
                self.name = str(Path(urlparse(url).path).name)
            if not self.path:
                self.path = str(Path(urlparse(url).path).parent)

    def add_location(self, loc: Union[str, FileLocation], set_as_default=False):
        """[summary]
        Add a location for this File (by string or existing FileLocation record).

        Args:
            loc (Union[str, FileLocation]): The location to add to this File.
            set_as_default (bool, optional): Make the new location the default. Defaults to False.
        """

        if isinstance(loc, FileLocation) and loc.file != self:
            raise ValueError(
                f"Cannot add a FileLocation instance that does not point to this File ({self.id})"
            )

        if isinstance(loc, str):
            loc = FileLocation(url=loc, file=self)

        try:
            if set_as_default:
                # we clear _dirty_location to ensure any existing unsaved location
                # on the file object doesn't clobber the default we are setting here
                self._dirty_location = None
                loc.set_as_default(save=True)
            else:
                loc.save()
        except (ValidationError, IntegrityError) as ex:
            if self.locations.filter(url=loc.url).exists():
                logger.warning(
                    f"Not creating duplicate location {loc.url} (File: {self.id})"
                )
            else:
                raise ex

    def remove_location(self, loc: Union[str, FileLocation], protect_default=True):
        """[summary]
        Remove a location for this File (by string or existing FileLocation record).

        Args:
            loc (Union[str, FileLocation]): The location to remove from this File.
            protect_default (bool, optional): If True, don't allow removing the default location. Defaults to True.
        """
        if isinstance(loc, str):
            loc = self.locations.filter(url=loc).first()

        if loc.default and protect_default:
            logger.warning(
                "Not removing default file location {loc.id} since protect_default=True"
            )
            return

        with transaction.atomic():
            loc.delete()
            if self.locations.filter(default=True).count() == 0:
                some_loc = self.locations.first()
                if some_loc:
                    some_loc.set_as_default(save=True)

    def delete_at_location(
        self,
        location: Union[str, FileLocation],
        allow_delete_default=False,
        delete_empty_directory=True,
    ):
        """
        Delete file content at a particular remote location.
        Takes a URL string or FileLocation object.
        To delete the 'default' location, allow_delete_default must be True
        - this ensures we don't accidentally delete the primary location unless
        we are explicit about it.

        By default, if the containing directory is empty after file deletion,
        it will also be removed (disable this behaviour using
        `delete_empty_directory=False`).

        :param location: The URL location or FileLocation to delete.
        :type location: Union[str, FileLocation]
        :param allow_delete_default: Allow deletion of the data at the default
                                     FileLocation.
        :type allow_delete_default: bool
        :param delete_empty_directory: Also removes the containing directory of
                                       the file if it's empty after deleting the file.
        :type delete_empty_directory: bool
        :return:
        :rtype:
        """

        if isinstance(location, str):
            fileloc = self.locations.filter(url=location).first()
        elif isinstance(location, FileLocation):
            fileloc = location
        else:
            raise TypeError(
                f"location must be a string or FileLocation, not a {type(location)}."
            )

        if fileloc is None:
            raise FileLocation.DoesNotExist()
        if fileloc.default and not allow_delete_default:
            raise ValueError("Cannot remove default FileLocation for this File")

        def _do_logical_delete():
            """
            Marks the database record as deleted without attempting to remove file
            content on storage.
            """
            with transaction.atomic():
                fileloc.delete()
                if self.locations.count() == 0:
                    self.deleted_time = timezone.now()
                    self.save()
                # Ensure there is always a default.
                else:
                    if self.locations.filter(default=True).count() == 0:
                        self.locations.first().set_as_default()

        @backoff.on_exception(
            backoff.expo, (socket.gaierror,), max_tries=3, jitter=backoff.full_jitter
        )
        def _delete_with_retries(_storage, _path: str):
            """Delete with retries upon network connection errors"""
            _storage.delete(_path)

        url = urlparse(fileloc.url)
        scheme = url.scheme

        if scheme == "laxy+sftp":
            compute = get_compute_resource_for_location(location)
            if compute.status == ComputeResource.STATUS_DECOMMISSIONED:
                _do_logical_delete()
                return
            if not compute.available:
                raise Exception(
                    f"Unable to delete file {self.id} at {url} (FileLocation {location.id}) "
                    f" - ComputeResource {compute.id} is {compute.status}."
                )

            try:
                path_on_compute = self._abs_path_on_compute(location=location)
                # if fileloc.file.exists(fileloc):
                if compute.sftp_storage.exists(path_on_compute):
                    _delete_with_retries(compute.sftp_storage, path_on_compute)

                containing_dir = os.path.normpath(str(Path(path_on_compute).parent))
                if delete_empty_directory and compute.sftp_storage.exists(
                    containing_dir
                ):
                    _dirs, _files = compute.sftp_storage.listdir(containing_dir)
                    if (
                        len(_files) == 0
                        and len(_dirs) == 0
                        and containing_dir
                        != os.path.normpath(compute.jobs_dir)  # just in case
                    ):
                        _delete_with_retries(compute.sftp_storage, containing_dir)

            except FileNotFoundError as ex:
                logger.info(f"File is missing at {fileloc.url} - marking as deleted.")

            except BaseException as ex:
                raise Exception(
                    f"Storage backend issue - failed to delete file: "
                    f"{self.id} at {fileloc.url} (FileLocation {fileloc.id}) :: {ex}"
                )

        else:
            raise NotImplementedError(
                "Only laxy+sftp:// internal URLs can be deleted at this time."
            )

        _do_logical_delete()

    def name_from_location(self):
        try:
            return str(Path(urlparse(self.location).path).name)
        except:
            return None

    def path_from_location(self):
        try:
            return str(Path(urlparse(self.location).path).parent)
        except:
            return None

    # TODO: This could be triggered via a post_save signal + async task upon
    # creation and when self.location changes
    def set_metadata_from_location(self, save=True):
        """
        Uses the location URL to update the filename and file
        size, possibly other metadata. This may be achieved by various
        mechanisms (HEAD and Content-Disposition for http/https URLs, os.stat
        for local file:// URLs, fallback to URL or path splitting).

        :return:
        :rtype:
        """
        filename, size = find_filename_and_size_from_url(self.location)
        self.name = filename
        if size is not None:
            self.metadata["size"] = size
        if save:
            self.save()

    def add_type_tag(self, tags: Union[List[str], str], save=True):
        """
        Add file type tag(s). These tags are intended to be used to flag a
        file as a specific type (eg, csv, tsv, fastq, bam), or for use with
        a particular external application (eg degust, jbrowse).

        Enforces uniqueness.

        :param tags: A single tag or a list of tags
        :type tags: Union[List[str], str]
        :param save: Automatically call save()
        :type save: bool
        :return:
        :rtype:
        """
        if isinstance(tags, str):
            tags = [tags]

        if self.metadata is None:
            self.metadata = OrderedDict()

        self.type_tags.extend(tags)
        self.type_tags = unique(self.type_tags)

        if save:
            self.save()

    def remove_type_tag(self, tags: Union[List[str], str], save=True):
        """
        Remove file type tag(s). Enforces uniqueness.

        :param tags: A single tag or a list of tags
        :type tags: Union[List[str], str]
        :param save: Automatically call save()
        :type save: bool
        :return:
        :rtype:
        """
        if self.metadata is None:
            return

        if isinstance(tags, str):
            tags = [tags]

        existing = unique(self.type_tags)
        if existing:
            for t in tags:
                try:
                    existing.remove(t)
                except ValueError:
                    continue
            self.type_tags = existing

        if save:
            self.save()

    @property
    def checksum_type(self) -> str:
        """
        Get the type (algorithm) of the checksum, eg md5.

        :return: The checksum type (algorithm), eg md5.
        :rtype: str
        """
        if ":" in self.checksum:
            return self.checksum.split(":", 1)[0]

    @property
    def checksum_hash(self) -> str:
        """
        Get the hash value eg f3c90181aae57b887a38c4e5fe73db0c.

        :return: The hash value, eg f3c90181aae57b887a38c4e5fe73db0c.
        :rtype: str
        """
        if ":" in self.checksum:
            return self.checksum.split(":", 1).pop()

    @property
    def checksum_hash_base64(self) -> str:
        """
        Assuming the hash is a hexdigest string, convert to and return the
        Base64 representation. Used for HTTP Digest headers.

        :return: Base64 encoded hash value.
        :rtype: str
        """
        c = self.checksum_hash
        if c:
            int_hash = int(c, 16)
            return base64.b64encode(
                int_hash.to_bytes(int(math.ceil(int_hash.bit_length() / 8)), "big")
            ).decode("ascii")

    @property
    def full_path(self):
        return str(Path(self.path) / Path(self.name))

    def _abs_path_on_compute(
        self, location: Union[str, FileLocation, None] = None
    ) -> str:

        if location is None:
            location = self.location

        location = str(location)

        url = urlparse(location)
        compute = get_compute_resource_for_location(location)
        if compute is None:
            raise Exception(f"Cannot extract ComputeResource ID from: {location}")

        base_dir = compute.extra.get(
            "base_dir", getattr(settings, "DEFAULT_JOB_BASE_PATH")
        )
        file_path = str(Path(base_dir) / Path(url.path).relative_to("/"))

        return file_path

    def _get_storage_class(self, location=None) -> Union[Storage, None]:
        if location is None:
            location = self.location
        return get_storage_class_for_location(location)

    # def file_at_location(self, location: Union[str, FileLocation]) -> Union[BufferedRandom, None]:
    #     from laxy_backend.tasks.download import request_with_retries
    #
    #     if isinstance(location, FileLocation):
    #         location = location.url
    #
    #     # assert location is not None and str(location).strip() != '', \
    #     #     f"File {self.id} location is empty. This isn't allowed and shouldn't ever happen."
    #     if location is None or str(location).strip() == '':
    #         logger.warning(f"File {self.id} location is empty. "
    #                        f"This isn't allowed and shouldn't ever happen.")
    #         return None
    #
    #     url = urlparse(location)
    #     scheme = url.scheme
    #     if scheme == 'laxy+sftp':
    #         storage = self._get_storage_class()
    #         file_path = self._abs_path_on_compute()
    #         filelike = storage.open(file_path)
    #         # setattr(filelike, 'name', self.name)
    #         return BufferedRandom(filelike)
    #
    #     # TODO: This needs to be carefully reworked or removed. The intention would be to refer to a mountpoint
    #     #       relative to the Laxy backend server filesystem (eg an NFS mount), however there is scope for
    #     #       reading arbitrary files on the server if implemented incorrectly.
    #     elif scheme == 'file':
    #         # raise NotImplementedError('file:// URLs are currently not supported')
    #         storage = self._get_storage_class()
    #         return BufferedRandom(storage.open(self.full_path))
    #
    #     elif scheme in ['http', 'https', 'ftp', 'ftps', 'data']:
    #         response = request_with_retries(
    #             'GET', location,
    #             stream=True,
    #             headers={},
    #             auth=None)
    #         filelike = response.raw
    #         filelike.decode_content = True
    #         return BufferedRandom(filelike)
    #
    #     else:
    #         raise NotImplementedError(f'Cannot provide file-like object for scheme: {scheme}')

    def _file(
        self, location: Union[str, FileLocation]
    ) -> Union[None, SFTPStorageFile, typing.IO[AnyStr]]:
        """
        Return a file-like object for the given location.

        (django.core.files.storage.File interface)
        """
        # return self.file_at_location(self.location)
        from laxy_backend.tasks.download import request_with_retries

        if isinstance(location, FileLocation):
            location = location.url

        url = urlparse(location)
        scheme = url.scheme
        if scheme == "laxy+sftp":
            buffer_size = 8192
            storage = self._get_storage_class(location=location)
            file_path = self._abs_path_on_compute(location=location)
            filelike = storage.open(file_path)
            # setattr(filelike, 'name', self.name)
            return filelike

        # TODO: This needs to be carefully reworked or removed. The intention would be to refer to a mountpoint
        #       relative to the Laxy backend server filesystem (eg an NFS mount), however there is scope for
        #       reading arbitrary files on the server if implemented incorrectly.
        elif scheme == "file":
            # raise NotImplementedError('file:// URLs are currently not supported')
            storage = self._get_storage_class()
            return storage.open(self.full_path)

        elif scheme in ["http", "https", "ftp", "ftps", "data"]:
            response = request_with_retries(
                "GET", self.location, stream=True, headers={}, auth=None
            )
            filelike = response.raw
            filelike.decode_content = True
            return filelike

        else:
            raise NotImplementedError(
                f"Cannot provide file-like object for scheme: {scheme}"
            )

    @property
    def file(self) -> Union[None, SFTPStorageFile, typing.IO[AnyStr]]:
        """
        Return a file-like object for the default location.

        (django.core.files.storage.File interface)
        """
        if (
            self.location is None
            or str(self.location).strip() == ""
            and not self._state.adding
        ):
            logger.warning(
                f"File {self.id} location is empty. "
                f"This isn't allowed and shouldn't ever happen."
            )
            return None

        return self._file(self.location)

    @property
    def size(self) -> Union[int, None]:
        """
        Get the file size from metadata or via the storage class, opportunistically caching the value in metadata.
        Assumes the file size never changes once cached.

        Returns None if there is no size and the storage backend cannot provide one.

        :return:
        :rtype:
        """
        size = None
        if has_method(self.metadata, "get"):
            size = self.metadata.get("size", None)
        try:
            if size is None and self.file is not None and hasattr(self.file, "size"):
                size = int(self.file.size)
                # set on demand
                self.metadata["size"] = size
                self.save(update_fields=["metadata"])
        except NotImplementedError as ex:
            pass
        except (
            FileNotFoundError,
            ssh_exception.SSHException,
            ComputeResourceDecommissioned,
        ):
            # Can occur when SFTP backend server is inaccessible
            # Decommissioned locations are no longer available to query, so we ignore those too
            pass

        return size

    @size.setter
    def size(self, value: int):
        self.metadata["size"] = int(value)

    @property
    def deleted(self):
        return bool(self.deleted_time)

    def delete_file(self):
        excn = None
        for location in self.locations.all():
            # Attempt delete on all even if one raises exception.
            # Defers the first exception thrown to be raised later
            try:
                self.delete_at_location(location, allow_delete_default=True)
            except BaseException as _ex:
                if excn is None:
                    excn = _ex

        if excn is not None:
            raise excn

    def exists(self, loc=None):
        if loc is None:
            loc = self.locations.filter(default=True).first()
        loc = str(loc)
        try:
            f = self._file(loc)
            if has_method(f, "exists"):
                return f.exists()
            elif isinstance(f, SFTPStorageFile):
                return f._storage.exists(f.name)
        except FileNotFoundError:
            return False

    def get_absolute_url(self):
        from django.urls import reverse

        url = reverse(
            "laxy_backend:file_download",
            kwargs={"uuid": self.uuid(), "filename": self.name},
        )
        return url


@receiver(pre_save, sender=File)
def auto_file_fields(sender, instance, raw, using, update_fields, **kwargs):
    """
    Set name and path on a File based on the location URL, if not specified.
    """
    if instance._state.adding and instance.location is not None:
        # Derive a name and path based on the location URL
        if not instance.name:
            instance.name = instance.name_from_location()
        if not instance.path:
            instance.path = instance.path_from_location()


def get_compute_resources_for_files(
    files: Union[Iterable, QuerySet]
) -> typing.Set[Union[ComputeResource, None]]:
    """
    Return the set of ComputeResources associated with the primary location of
    a set of Files. If some files have no primary location, None will be included.

    eg.

    >>> get_compute_resources_for_files(job.get_files())
    {<ComputeResource: ComputeResource object (Zk4BZgcDDfRZGfXYismNBC)>}

    :param files: A list, iterable or QuerySet of Files.
    :type files: Union[Iterable, QuerySet]
    :return: A set of ComputeResource instances, including None.
    :rtype: Set[Union[ComputeResource, None]]
    """
    if isinstance(files, QuerySet):
        # files = files.prefetch_related("locations")  # .only("locations")
        locations = files.filter(locations__default=True).values_list("locations__url")
        compute_ids = set(
            [get_compute_resource_str_for_location(l[0]) for l in locations]
        )
        return set(ComputeResource.objects.filter(pk__in=compute_ids))
    else:
        return set([get_compute_resource_for_location(f.location) for f in files])


def get_primary_compute_location_for_files(
    files: Union[Iterable, QuerySet]
) -> Union[ComputeResource, None]:
    """
    Given some Files, return the single primary ComputeResource where they are stored, if there is one.
    If the files are spread across multiple ComputeResource locations (or some are missing locations),
    returns None.

    :param files: A list, iterable or QuerySet of Files.
    :type files: Union[Iterable, QuerySet]
    :return: The ComputeResource where the files reside, or None.
    :rtype: Union[ComputeResource, None]
    """
    stored_at = get_compute_resources_for_files(files)
    if len(stored_at) == 1:
        return stored_at.pop()

    return None


@reversion.register()
class FileSet(Timestamped, UUIDModel):
    """
    A set of files. Might be used to represent a directory.

    name - A free-text human readable name/description for the fileset.
    path - A directory name or forward-slashed path associated with the FileSet.
    files - The files in this FileSet (RelatedManager from File).
    """

    name = CharField(max_length=2048)
    path = CharField(max_length=4096, blank=True, null=True)

    owner = ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, related_name="filesets"
    )

    # a list of File ids eg ['2VSd4mZvmYX0OXw07dGfnV', '3XSd4mZvmYX0OXw07dGfmZ']
    # old_file_list = ArrayField(CharField(max_length=22), blank=True, default=list)

    # IDEA: a list of FileSet ids (effectively like subdirectories) ?
    # filesets = ArrayField(CharField(max_length=22), blank=True, default=list)

    @transaction.atomic
    def add(self, files: Union[File, Iterable[File]], save=True):
        """
        Add a File or Files to the FileSet. Takes a single File object,
        or a list of Files. Files passed to the method are always saved
        (via File.save()).

        :param files: A single File object or a list of File objects.
        :type files: File | Iterable
        :param save: If True, save this FileSet after adding files.
        :type save: bool
        :return: None
        :rtype: NoneType
        """
        if not isinstance(files, Iterable):
            files = [files]

        # we ensure all Files in the list are unique
        files = unique(files)

        # TODO: Is this transaction slow ? Profile things.
        with transaction.atomic():
            # unsaved Files must be saved before calling self.files.add
            [f.save() for f in files if not f.pk]

            # Files inherit the owner of the FileSet
            # (unless the FileSet has no owner)
            if self.owner:
                for f in files:
                    f.owner = self.owner

            # bulk=False causes Files the File.save() method to be called for
            # each file, including pre_save/post_save hooks.
            self.files.add(*files, bulk=False)

            self.modified_time = timezone.now()

            for job in self.jobs():
                job.modified_time = timezone.now()
                job.save()

            if save:
                self.save()

    @transaction.atomic
    def remove(self, files: Union[File, Iterable[File]], save=True, delete=False):
        """
        Remove a File or Files to the FileSet. Takes a File object or a list
        of Files.

        :param files: A single File object or a list of File objects.
        :type files: File | Iterable
        :param save: If True, save this FileSet after removing files.
        :type save: bool
        :param delete: Delete the Files after removing them from this FileSet
                       (doesn't check if other FileSets or database objects still
                        hold a reference to this file, in the case that they are
                        using non-relational JSON blobs)
        :type delete: bool
        :return: None
        :rtype: NoneType
        """
        if not isinstance(files, Iterable):
            files = [files]

        files = unique(files)

        with transaction.atomic():
            # bulk=False causes Files the File.delete() method to be called for
            # each file, including pre_save/post_save hooks.
            self.files.remove(*files, bulk=False)

            if delete:
                [f.delete() for f in files]

            self.modified_time = timezone.now()

            for job in self.jobs():
                job.modified_time = timezone.now()
                job.save()

            if save:
                self.save()

    def get_files(self) -> QuerySet:
        """
        Return all the File objects associated with this FileSet.

        :return: The File object in this FileSet (as a Django QuerySet).
        :rtype: django.models.query.QuerySet(File)
        """
        # TODO: Remove ordering here to optimize, order only where required ?
        # TODO: select_related or prefetch_related here ?
        return self.files.order_by("path", "name")

    def get_files_by_path(self, file_path: Union[str, Path]) -> QuerySet:
        fname = Path(file_path).name
        fpath = Path(file_path).parent
        queryset = self.get_files().filter(name=fname, path=fpath)
        return queryset

    def get_file_by_path(self, file_path: Union[str, Path]) -> File:
        fname = Path(file_path).name
        fpath = Path(file_path).parent
        f = self.get_files().filter(name=fname, path=fpath).first()
        return f

    def jobs(self) -> Union[QuerySet, None]:
        """
        Return all Jobs associated with this FileSet, as a QuerySet.
        In most cases, this is likely to be a single Job.

        :return: A QuerySet of Jobs that reference this FileSet.
        :rtype: QuerySet
        """
        # return Job.objects.filter(Q(input_files=self.id) | Q(output_files=self.id)).all()
        return self.jobs_as_input.union(self.jobs_as_output.all()).all()

    @property
    def job(self) -> Union[Job, None]:
        """
        Return the oldest Job associated with the FileSet.

        :return: The oldest associated job instance based on created_time.
        :rtype: Job
        """
        j = self.jobs()
        if j is not None:
            # Oldest Job first
            return j.order_by("created_time").first()


@reversion.register()
class SampleCart(Timestamped, UUIDModel):
    """
    A set of samples for a pipeline run. This often reflects the state of the 'sample cart'
    when setting up a job via the web frontend.

    name - A short friendly name for the sample cart.
    samples - A JSON blob representing each 'sample' and the associated URLs or File IDs.
    owner - The User who owns this object.
    """

    name = CharField(max_length=2048, blank=True, null=True)
    owner = ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="samplecarts",
    )

    # TODO: Should we put a validator on here to ensure the
    # basic object shape and required fields are present ?
    # Maybe with jsonschema:
    # https://medium.com/@aleemsaadullah/adding-validation-support-for-jsonfield-in-django-2e26779dccc
    # https://github.com/Julian/jsonschema
    # Generate JSON Schema from a (type-hinted) Python object: https://pydantic-docs.helpmanual.io/#schema-creation
    # It might make more sense to create a DRF Serializer and use that as a validator.
    samples = JSONField(default=list)

    job = ForeignKey(
        Job, blank=True, null=True, on_delete=models.CASCADE, related_name="samplecarts"
    )

    # 'samples' is a dictionary keyed by sample name, with a list of files grouped by
    # merge_group and pair (a merge_group could be a set of equivalent lanes the sample
    # was split across, or a technical replicate):
    #
    # Equivalent samples (technical replicates) in different lanes can be merged -
    # they could also be thought of as split FASTQ files.

    # Structure:
    # [{"name": "sampleName",
    #   "files": [{"R1": "R1_lane1", "R2": "R2_lane1"},
    #             {"R1": "R1_lane2", "R2": "R2_lane2"}]}]

    # A single 'sampleName' actually corresponds to a Sample+Condition+BiologicalReplicate.

    # *TODO*: Change this to files: [{R1: {location: "http://foo/bla.txt", name: "bla.txt}] form
    #         shaped like a subset of models.File fields.

    # For two samples (R1, R2 paired end) split across two lanes, using File UUIDs
    #
    # [
    #    {
    #         "name": "sample_wildtype",
    #         "files": [
    #             {
    #                 "R1": "2VSd4mZvmYX0OXw07dGfnV",
    #                 "R2": "3XSd4mZvmYX0OXw07dGfmZ"
    #             },
    #             {
    #                 "R1": "Toopini9iPaenooghaquee",
    #                 "R2": "Einanoohiew9ungoh3yiev"
    #             }]
    #     },
    #     {
    #         "name": "sample_mutant",
    #         "files": [
    #             {
    #                 "R1": "zoo7eiPhaiwion6ohniek3",
    #                 "R2": "ieshiePahdie0ahxooSaed"
    #             },
    #             {
    #                 "R1": "nahFoogheiChae5de1iey3",
    #                 "R2": "Dae7leiZoo8fiesheech5s"
    #             }]
    #     }
    # ]
    #
    #
    # We would merge the R1s together for a sample and the R2s together for a sample:
    # eg, merge "2VSd4mZvmYX0OXw07dGfnV" with "Toopini9iPaenooghaquee"
    #     and   "3XSd4mZvmYX0OXw07dGfmZ" with "Einanoohiew9ungoh3yiev"
    # ..etc.. as technical replicates

    def from_csv(
        self,
        csv_string: Union[str, Sequence],
        header=False,
        dialect="excel",
        encoding="utf-8-sig",
        comment_char="#",
        save=True,
    ):
        """
        Accepts a raw string, or a pre-parsed list-of-lists (eg from Python's csv.reader)

        CSV format:

        # Sample Name, R1 file, R2 file
        SampleA, ftp://bla_lane1_R1.fastq.gz, ftp://bla_lane1_R2.fastq.gz
        SampleA, ftp://bla_lane2_R1.fastq.gz, ftp://bla_lane2_R2.fastq.gz
        SampleB, ftp://bla2_R1_001.fastq.gz, ftp://bla2_R2_001.fastq.gz
               , ftp://bla2_R1_002.fastq.gz, ftp://bla2_R2_002.fastq.gz
        SampleC, ftp://foo2_lane4_1.fastq.gz, ftp://foo2_lane4_2.fastq.gz
        SampleC, ftp://foo2_lane5_1.fastq.gz, ftp://foo2_lane5_2.fastq.gz
        ------

        Sample name actually corresponds to Sample+Condition+BiologicalReplicate
        (eg an ID for both the sample, replicate and condition/treatment)

        :param csv_string:
        :type csv_string:
        :return:
        :rtype:
        """
        samples = OrderedDict()
        prev_sample_name = None

        if isinstance(csv_string, bytes):
            csv_string = csv_string.decode(encoding)

        if isinstance(csv_string, str):
            lines = list(csv.reader(csv_string.splitlines(), dialect=dialect))
        elif isinstance(csv_string, collections.abc.Sequence):
            lines = csv_string
        else:
            raise TypeError("csv_string must be a string or Sequence (eg list, tuple)")

        if header:  # skip header
            lines = lines[1:]

        for line in lines:
            fields = line
            # skip empty lines
            if not fields:
                continue
            sample_name = fields[0].strip()

            if sample_name == "":
                if prev_sample_name:
                    sample_name = prev_sample_name
                else:
                    raise ValueError("First row sample name cannot be blank")

            if sample_name not in samples:
                samples[sample_name] = []

            # TODO: Convert URLs into UUIDs
            #       Files may be specified as (existing) UUIDs or URLs.
            #       If they are URLs, create (or lookup) associated file objects
            #       for that user

            pair = OrderedDict(
                {
                    f"R{n + 1}": {
                        "location": file.strip(),
                        "name": find_filename_and_size_from_url(file.strip())[0],
                    }
                    for n, file in enumerate(fields[1:])
                }
            )
            samples[sample_name].append(pair)
            prev_sample_name = sample_name

        # We initially create a structure like:
        # {sampleName: [{"R1": {"location": fileUrl1, "name": filename1},
        #                "R2": {"location": fileUrl2, "name": filename2}}]},
        # Then convert to [{name: sampleName, files: [ ... ]},]
        sample_list = []
        for sample_name, files in samples.items():
            sample_list.append({"name": sample_name, "files": files})

        self.samples = sample_list
        if save:
            self.save()

    def to_csv(self, newline="\r\n"):
        lines = []
        for sample in self.samples:
            sample_name = sample.get("name")
            for pair in sample.get("files", {}):
                r1 = pair.get("R1", "")
                r2 = pair.get("R2", "")
                # Deal with {R1: str} or {R1: {location: str, name: str}} shapes in database
                locations = []
                for p in [r1, r2]:
                    if isinstance(p, str):
                        locations.append(p)
                    if isinstance(p, dict):
                        locations.append(p.get("location", ""))
                lines.append(",".join([sample_name] + locations))

        # TODO: Optionally convert File UUIDs into URLs

        return newline.join(lines)


# NOTE: We could bypass this signal in special cases using:
#       https://github.com/RobertKolner/django-signal-disabler
@receiver(pre_save, sender=SampleCart)
def prevent_samplecart_update_after_job_assigned(
    sender, instance: SampleCart, raw, using, update_fields, **kwargs
):
    """
    Prevents a SampleCart being updated once it has been attached to a Job.
    """
    try:
        obj: SampleCart = sender.objects.get(pk=instance.pk)
        if obj.job:
            raise RuntimeError(
                "Updating a SampleCart once the job field is set is not allowed."
            )
    except sender.DoesNotExist:
        pass


@reversion.register()
class PipelineRun(Timestamped, UUIDModel):
    owner = ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="pipeline_runs",
    )

    # NOTE: This may become a ForeignKey pointing to a Pipeline definition
    #       Currently it's intended to be a pipeline name used as an identifier
    #       (eg, used to run the correct job script, possibly on a suitable
    #        ComputeResource)
    pipeline = CharField(max_length=256, blank=True, null=True)

    sample_cart = ForeignKey(
        SampleCart,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="pipeline_runs",
    )

    # input_fileset = ForeignKey(FileSet,
    #                            blank=True,
    #                            null=True,
    #                            on_delete=models.SET_NULL,
    #                            related_name='pipeline_runs')

    # Sample metadata, keyed by sample name
    # - eg, mapping sample names to conditions
    # {"SampleA": { "conditions": ["wt", "ugly"]},
    #  "SampleB": { "conditions": ["mutant"]} }
    # sample_metadata = JSONField(default=OrderedDict)

    # Parameters specific to the pipeline (eg reference genome)
    params = JSONField(default=OrderedDict)

    # Free-text comment, mostly for users to help keep track of runs.
    description = CharField(max_length=2048, blank=True, null=True)


def _generate_access_token_string():
    """
    Generate a pseudo-random URL-safe string for use as an access token in a URL query parameter,
    eg ?access_token=af4a9c52-1dd7-4c69-af70-5c364173214b

    (The style of this string is intentionally different to the Base62-encoded UUID4's used as
     object primary keys, so they can be easily differentiated by users and in debugging).

    :return: A pseudo-random string.
    :rtype: str
    """
    return str(uuid4())


@reversion.register()
class AccessToken(Timestamped, UUIDModel):
    """
    Intended to allow read-only access to the target object (obj / object_id) to
    the bearer. Optional expiry time, if set.
    """

    owner_field_name = "created_by"

    token = CharField(
        db_index=True,
        max_length=64,
        blank=False,
        null=False,
        default=_generate_access_token_string,
    )
    expiry_time = DateTimeField(blank=True, null=True)
    created_by = ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="access_tokens",
    )

    content_type = ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    object_id = CharField(db_index=True, null=True, max_length=24)
    obj = GenericForeignKey("content_type", "object_id")

    def is_valid(self, target_obj: Union[UUIDModel, str] = None):
        if self.expiry_time is not None and (timezone.now() < self.expiry_time):
            return False

        if isinstance(target_obj, str):
            return self.object_id == target_obj
        if isinstance(target_obj, UUIDModel):
            ct = ContentType.objects.get_for_model(target_obj)
            return self.object_id == target_obj.id and self.content_type == ct
