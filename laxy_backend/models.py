from django.core.handlers.wsgi import WSGIRequest
from typing import List, Union
from collections import OrderedDict, Sequence
from datetime import datetime
import math
import json
import csv
from pathlib import Path
from urllib.parse import urlparse
import base64
from uuid import uuid4
from io import StringIO, BytesIO

import rows
from paramiko.rsakey import RSAKey

from django.conf import settings
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import models, transaction
from django.core.files.storage import get_storage_class
from django.core.serializers import serialize
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db.models import Model, CharField, URLField, ForeignKey, BooleanField, IntegerField, DateTimeField, QuerySet
from django.contrib.postgres.fields import ArrayField
# from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import reversion
from rest_framework.authtoken.models import Token

from .tasks import orchestration
from .cfncluster import generate_cluster_stack_name
from .util import (unique,
                   generate_uuid,
                   generate_secret_key,
                   find_filename_and_size_from_url,
                   laxy_sftp_url)

import logging

logger = logging.getLogger(__name__)

if 'postgres' not in settings.DATABASES['default']['ENGINE']:
    from jsonfield import JSONField
else:
    from django.contrib.postgres.fields import JSONField

SCHEME_STORAGE_CLASS_MAPPING = {
    'file': 'django.core.files.storage.FileSystemStorage',
    'sftp': 'storages.backends.sftpstorage.SFTPStorage',
    'laxy+sftp': 'storages.backends.sftpstorage.SFTPStorage',

}
"""
Maps URL schemes to Django storage backends that can handle them.
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

    schemes = ('http',
               'https',
               'ftp',
               'sftp',
               'laxy+sftp',
               's3',
               'magnet',
               'file',
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
        get_latest_by = ['-modified_time']

    created_time = DateTimeField(auto_now_add=True)
    modified_time = DateTimeField(auto_now=True)


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

    id = CharField(primary_key=True,
                   editable=False,
                   max_length=24,
                   default=generate_uuid)

    def uuid(self):
        return self.id

    def __unicode__(self):
        return self.id


class User(AbstractUser, UUIDModel):
    pass


class UserProfile(models.Model):
    user = models.OneToOneField(User,
                                primary_key=True,
                                on_delete=models.CASCADE,
                                blank=False,
                                related_name='profile')
    image_url = models.URLField(blank=True, null=True)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created or not UserProfile.objects.filter(user=instance).exists():
        UserProfile.objects.create(user=instance)
    instance.profile.save()


class JSONSerializable:
    def to_json(self):
        return serialize('json', self)


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
        ordering = ['-timestamp']
        get_latest_by = ['timestamp']

    user = ForeignKey(User,
                      blank=True,
                      null=True,
                      on_delete=models.SET_NULL,
                      related_name='event_logs')
    timestamp = DateTimeField(default=timezone.now, db_index=True)
    event = CharField(max_length=64)
    message = CharField(max_length=256,
                        blank=True,
                        null=True)
    extra = JSONField(default=OrderedDict)

    content_type = ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    object_id = CharField(null=True, max_length=24, db_index=True)
    obj = GenericForeignKey('content_type', 'object_id')

    @staticmethod
    def log(event, message='', user=None, extra=None, obj=None, timestamp=None):
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
            timestamp=timestamp
        )
        return event


@reversion.register()
class ComputeResource(Timestamped, UUIDModel):
    # model created, no actual resource yet
    STATUS_CREATED = 'created'
    # actual resource is being created
    STATUS_STARTING = 'starting'
    # resource is online and functioning as expected
    STATUS_ONLINE = 'online'
    # resource isn't functioning correctly. may be temporary.
    STATUS_ERROR = 'error'
    # resource is intentionally offline and shouldn't be used. may be temporary.
    STATUS_OFFLINE = 'offline'
    # resource is being decommissioned and shouldn't be used. permanent.
    STATUS_TERMINATING = 'terminating'
    # resource has been decommissioned and won't be available. permanent.
    STATUS_DECOMMISSIONED = 'decommissioned'

    COMPUTE_STATUS_CHOICES = ((STATUS_CREATED, 'object_created'),
                              (STATUS_STARTING, 'starting'),
                              (STATUS_ONLINE, 'online'),
                              (STATUS_ERROR, 'error'),
                              (STATUS_OFFLINE, 'offline'),
                              (STATUS_TERMINATING, 'terminating'),
                              (STATUS_DECOMMISSIONED, 'decommissioned'),
                              )

    owner = ForeignKey(User,
                       blank=True,
                       null=True,
                       on_delete=models.CASCADE,
                       related_name='compute_resources')
    status = CharField(max_length=64,
                       choices=COMPUTE_STATUS_CHOICES,
                       default=STATUS_CREATED)

    host = CharField(max_length=255, blank=True, null=True)
    gateway_server = CharField(max_length=255, blank=True, null=True)
    disposable = BooleanField(default=True)
    name = CharField(max_length=128, blank=True, null=True)

    # QUEUE_TYPE_LOCAL = 'local'  # a regular process (via the shell) on a compute node
    # QUEUE_TYPE_SLURM = 'slurm'  # submit the job to a slurm queue on the compute node
    #
    # QUEUE_TYPE_CHOICES = ((QUEUE_TYPE_LOCAL, 'local'),
    #                       (QUEUE_TYPE_SLURM, 'slurm'),
    #                       )
    # queue_type = CharField(max_length=64,
    #                        choices=QUEUE_TYPE_CHOICES,
    #                        default=QUEUE_TYPE_LOCAL)
    '''
    The host `queue_type` is used for logic around how the host is used 
    (job submission, monitoring and cancellation).
    eg, values might be 'local' or 'slurm'.
    '''

    # This contains resource type specific data, eg it may contain
    # ssh keys, queue type
    extra = JSONField(default=OrderedDict)

    def running_jobs(self):
        """
        Returns a Django QuerySet of all the jobs currently running or
        on this compute resource.

        :return: The pending Jobs
        :rtype: django.db.models.query.QuerySet
        """
        return Job.objects.filter(compute_resource=self,
                                  status=Job.STATUS_RUNNING)

    def pending_jobs(self):
        """
        Returns a Django QuerySet of all the jobs currently running or
        waiting to run on this compute resource.

        :return: The pending Jobs
        :rtype: django.db.models.query.QuerySet
        """
        return Job.objects.filter(compute_resource=self,
                                  status__in=[Job.STATUS_CREATED,
                                              Job.STATUS_RUNNING,
                                              Job.STATUS_STARTING])

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
                args=({'compute_resource_id': self.id},))
        else:
            return False

    @property
    def private_key(self):
        return base64.b64decode(self.extra.get('private_key')).decode('ascii')

    @property
    def hostname(self):
        return self.host.split(':')[0]

    @property
    def port(self):
        if ':' in self.host:
            return self.host.split(':').pop()
        else:
            return None

    @property
    def queue_type(self):
        return self.extra.get('queue_type', None)

    @queue_type.setter
    def queue_type(self, queue_type: str):
        self.extra['queue_type'] = queue_type
        self.save()


@reversion.register()
class Job(Timestamped, UUIDModel):
    """
    Represents a processing job (typically a long running remote job managed
    by a Celery task queue).
    """
    STATUS_CREATED = 'created'
    STATUS_HOLD = 'hold'
    STATUS_STARTING = 'starting'
    STATUS_RUNNING = 'running'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETE = 'complete'

    JOB_STATUS_CHOICES = ((STATUS_CREATED, 'object_created'),
                          (STATUS_HOLD, 'hold'),
                          (STATUS_STARTING, 'starting'),
                          (STATUS_RUNNING, 'running'),
                          (STATUS_FAILED, 'failed'),
                          (STATUS_CANCELLED, 'cancelled'),
                          (STATUS_COMPLETE, 'complete'),
                          )

    owner = ForeignKey(User,
                       on_delete=models.SET_NULL,
                       blank=True,
                       null=True,
                       related_name='jobs')
    secret = CharField(max_length=255,
                       blank=True,
                       null=True,
                       default=generate_secret_key)
    status = CharField(max_length=64,
                       choices=JOB_STATUS_CHOICES,
                       default=STATUS_CREATED)
    exit_code = IntegerField(blank=True, null=True)
    remote_id = CharField(max_length=64, blank=True, null=True)

    # jsonfield or native Postgres
    # params = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})

    # django-jsonfield or native Postgres
    params = JSONField(default=OrderedDict)

    # A JSON-serializable params class that may be specialized via
    # multiple-table inheritance
    # params = ForeignKey(JobParams,
    #                     blank=True,
    #                     null=True,
    #                     on_delete=models.SET_NULL)

    input_files = ForeignKey('FileSet', null=True, blank=True,
                             related_name='jobs_as_input',
                             on_delete=models.CASCADE)
    output_files = ForeignKey('FileSet', null=True, blank=True,
                              related_name='jobs_as_output',
                              on_delete=models.CASCADE)

    compute_resource = ForeignKey(ComputeResource,
                                  blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL,
                                  related_name='jobs')

    completed_time = DateTimeField(blank=True, null=True)

    @transaction.atomic()
    def _init_filesets(self, save=True):
        if not self.input_files:
            self.input_files = FileSet(name=f'Input files for job: {self.id}',
                                       path='input',
                                       owner=self.owner)
            if save:
                self.input_files.save()

        if not self.output_files:
            self.output_files = FileSet(name=f'Output files for job: {self.id}',
                                        path='output',
                                        owner=self.owner)
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

    def latest_event(self):
        try:
            return EventLog.objects.filter(
                object_id=self.id).exclude(
                event__exact='JOB_STATUS_CHANGED').latest()
        except EventLog.DoesNotExist:
            return EventLog.objects.none()

    def get_files(self) -> models.query.QuerySet:
        # Combine querysets
        return self.input_files.get_files() | self.output_files.get_files()

    @property
    def done(self):
        """
        Returns True if the job has finished, either successfully
        or unsuccessfully.

        :return: True if job is no longer running.
        :rtype: bool
        """
        return (self.status == Job.STATUS_COMPLETE or
                self.status == Job.STATUS_CANCELLED or
                self.status == Job.STATUS_FAILED)

    @transaction.atomic()
    def add_files_from_tsv(self,
                           tsv_table: Union[List[dict], str, bytes],
                           save=True):
        """

        ```tsv
        filepath	checksum	type_tags	metadata
        input/some_dir/table.txt	md5:7d9960c77b363e2c2f41b77733cf57d4	text,csv,google-sheets	{}
        input/some_dir/sample1_R2.fastq.gz	md5:d0cfb796d371b0182cd39d589b1c1ce3	fastq	{}
        input/some_dir/sample2_R2.fastq.gz	md5:a97e04b6d1a0be20fcd77ba164b1206f	fastq	{}
        output/sample2/alignments/sample2.bam	md5:7c9f22c433ae679f0d82b12b9a71f5d3	bam,alignment,bam.sorted,jbrowse	{}
        output/sample2/alignments/sample2.bai	md5:e57ea180602b69ab03605dad86166fa7	bai,jbrowse	{}
        ```

        :param tsv_table:
        :type tsv_table:
        :param save:
        :type save:
        :return:
        :rtype:
        """
        from laxy_backend.serializers import FileBulkRegisterSerializer

        # https://colab.research.google.com/drive/1pWRRlthtJ1FGjmPJLRivlsJk716Ckaze
        if isinstance(tsv_table, str) or isinstance(tsv_table, bytes):
            table = rows.import_from_csv(BytesIO(tsv_table), skip_header=False)
            table = json.loads(rows.export_to_json(table))
        elif isinstance(tsv_table, list):
            table = tsv_table
        else:
            raise ValueError("tsv_table must be str, bytes or a list of dicts")

        in_files = []
        out_files = []

        self._init_filesets()

        for row in table:
            f = FileBulkRegisterSerializer(data=row)
            if f.is_valid(raise_exception=True):

                # Check if file exists by path in input/output filesets already,
                # if so, update existing file
                fullpath = Path(f.validated_data['path']) / Path(f.validated_data['name'])
                existing_infile = self.input_files.get_files_by_path(fullpath).first()
                existing_outfile = self.output_files.get_files_by_path(fullpath).first()
                for existing in [existing_infile, existing_outfile]:
                    if existing:
                        f = FileBulkRegisterSerializer(existing,
                                                       data=row, partial=True)
                        f.is_valid(raise_exception=True)
                        f_obj = f.instance

                if not any([existing_infile, existing_outfile]):
                    f_obj = f.create(f.validated_data)

                f_obj.owner = self.owner
                if not f_obj.location and self.compute_resource is not None:
                    location_base = laxy_sftp_url(self)
                    f_obj.location = f'{location_base}/{f_obj.path}/{f_obj.name}'
                if save:
                    f_obj = f.save()

            pathbits = Path(f.validated_data.get('path', '').strip('/')).parts
            if pathbits and pathbits[0] == 'input':
                self.input_files.add(f_obj)
                in_files.append(f_obj)

            elif pathbits and pathbits[0] == 'output':
                self.output_files.add(f_obj)
                out_files.append(f_obj)

            else:
                logger.debug(f"Not adding file {f_obj.full_path} ({f_obj.id}) "
                             f"- File paths for a Job must begin with input/ or output/")
                # raise ValueError("File paths for a Job must begin with input/ or output/")

        return in_files, out_files


# Alternatives to a pre_save signal here might be using:
# https://github.com/kajic/django-model-changes which gives a more streamlined
# way of watching fields via pre/post_save signals
# or using properties on the model:
# https://www.stavros.io/posts/how-replace-django-model-field-property/
@receiver(pre_save, sender=Job)
def update_job_completed_time(sender, instance,
                              raw, using, update_fields, **kwargs):
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
            instance.completed_time = datetime.now()


@receiver(pre_save, sender=Job)
def job_status_changed_event_log(sender, instance,
                                 raw, using, update_fields, **kwargs):
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
                'JOB_STATUS_CHANGED',
                message=f"Job status changed: {obj.status} → {instance.status}",
                user=instance.owner,
                obj=obj,
                extra=OrderedDict({'from': obj.status, 'to': instance.status}))


@receiver(pre_save, sender=Job)
def job_init_filesets(sender, instance: Job,
                      raw, using, update_fields, **kwargs):
    instance._init_filesets()


@receiver(post_save, sender=Job)
def new_job_event_log(sender, instance, created,
                      raw, using, update_fields, **kwargs):
    """
    Creates an event log entry every time a Job is created.
    """
    if created:
        EventLog.log(
            'JOB_STATUS_CHANGED',
            message="Job created.",
            user=instance.owner,
            obj=instance,
            extra={'from': None, 'to': instance.status})


@reversion.register()
class File(Timestamped, UUIDModel):
    class Meta:
        indexes = [
            models.Index(fields=['path', 'name']),
            models.Index(fields=['fileset', 'path', 'name']),
        ]

        # TODO: Enforce unique path/name within a FileSet ?
        # unique_together = ('fileset', 'path', 'name')

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
    owner = ForeignKey(User, on_delete=models.CASCADE,
                       blank=True,
                       null=True,
                       related_name='files')
    # The URL to the file. Could be file://, https://, s3://, sftp://
    location = ExtendedURIField(max_length=2048, blank=False, null=False)

    fileset = ForeignKey('FileSet', related_name='files', null=True,
                         on_delete=models.SET_NULL)

    type_tags = ArrayField(models.CharField(max_length=255),
                           default=list,
                           null=True,
                           blank=True)

    # Arbitrary metadata.
    metadata = JSONField(default=OrderedDict)

    # metadata = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})

    # There is no direct link from File->Job, instead we use FileSet->Job.
    # This way, Files represent a single unique file (on disk, or at a URL),
    # and FileSets can represent a set of files used
    # as input/output of a Job.
    # job = ForeignKey(Job,
    #                  on_delete=models.CASCADE,
    #                  related_name='files')

    def name_from_location(self):
        try:
            return Path(urlparse(self.location).path).name
        except:
            return None

    def path_from_location(self):
        try:
            return Path(urlparse(self.location).path).parent
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
            self.metadata['size'] = size
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
        if ':' in self.checksum:
            return self.checksum.split(':', 1)[0]

    @property
    def checksum_hash(self) -> str:
        """
        Get the hash value eg f3c90181aae57b887a38c4e5fe73db0c.

        :return: The hash value, eg f3c90181aae57b887a38c4e5fe73db0c.
        :rtype: str
        """
        if ':' in self.checksum:
            return self.checksum.split(':', 1).pop()

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
                int_hash.to_bytes(
                    int(math.ceil(int_hash.bit_length() / 8)), 'big')
            ).decode('ascii')

    @property
    def full_path(self):
        return Path(self.path) / Path(self.name)

    @property
    def file(self):
        from laxy_backend.tasks.download import request_with_retries

        url = urlparse(self.location)
        scheme = url.scheme
        storage_class = get_storage_class(
            SCHEME_STORAGE_CLASS_MAPPING.get(scheme, None))
        if scheme == 'laxy+sftp':
            if '.' in url.netloc:
                raise NotImplementedError(
                    "ComputeResource UUID appears invalid.")
            # use netloc not hostname, since hostname forces lowercase
            compute_id = url.netloc
            try:
                compute = ComputeResource.objects.get(id=compute_id)
            except ComputeResource.DoesNotExist as e:
                raise e

            host = compute.hostname
            port = compute.port
            if port is None:
                port = 22
            private_key = compute.private_key
            username = compute.extra.get('username')
            base_dir = compute.extra.get('base_dir')
            params = dict(port=port,
                          username=username,
                          pkey=RSAKey.from_private_key(StringIO(private_key)))
            # storage = SFTPStorage(host=host, params=params)
            storage = storage_class(host=host, params=params)
            file_path = str(Path(base_dir) / Path(url.path).relative_to('/'))

            filelike = storage.open(file_path)
            # setattr(filelike, 'name', self.name)
            return filelike

        # TODO: This needs to be carefully reworked or removed. The intention would be to refer to a mountpoint
        #       relative to the Laxy backend server filesystem (eg an NFS mount), however there is scope for
        #       reading arbitrary files on the server if implemented incorrectly.
        elif scheme == 'file':
            # raise NotImplementedError('file:// URLs are currently not supported')
            return storage_class(location='/').open(self.full_path)
        else:
            response = request_with_retries(
                'GET', self.location,
                stream=True,
                headers={},
                auth=None)
            filelike = response.raw
            filelike.decode_content = True
            return filelike

    def get_absolute_url(self):
        from django.urls import reverse
        url = reverse('laxy_backend:file_download',
                      kwargs={'uuid': self.uuid(), 'filename': self.name})
        return url


@receiver(pre_save, sender=File)
def auto_file_fields(sender, instance, raw, using, update_fields, **kwargs):
    """
    Set name and path on a File based on the location URL, if not specified.
    """
    if instance._state.adding is True:
        # Derive a name and path based on the location URL
        if not instance.name:
            instance.name = instance.name_from_location()
        if not instance.path:
            instance.path = instance.path_from_location()


@reversion.register()
class FileSet(Timestamped, UUIDModel):
    """
    A set of files. Might be used to represent a directory.

    name - The set name (eg directory name)
    files - The files in this FileSet (RelatedManager from File)
    """

    name = CharField(max_length=2048)
    path = CharField(max_length=4096, blank=True, null=True)

    owner = ForeignKey(User,
                       on_delete=models.CASCADE,
                       blank=True,
                       null=True,
                       related_name='filesets')

    # a list of File ids eg ['2VSd4mZvmYX0OXw07dGfnV', '3XSd4mZvmYX0OXw07dGfmZ']
    # old_file_list = ArrayField(CharField(max_length=22), blank=True, default=list)

    # IDEA: a list of FileSet ids (effectively like subdirectories) ?
    # filesets = ArrayField(CharField(max_length=22), blank=True, default=list)

    @transaction.atomic
    def add(self, files: Union[File, List[File]], save=True):
        """
        Add a File or Files to the FileSet. Takes a single File object,
        or a list of Files. Files passed to the method are always saved
        (via File.save()).

        :param files: A single File object or a list of File objects.
        :type files: File | Sequence[File]
        :return: None
        :rtype: NoneType
        """
        if not isinstance(files, Sequence):
            files = [files]

        # we ensure all Files in the list are unique
        files = unique(files)

        with transaction.atomic():
            # unsaved Files must be saved before calling self.files.add
            [f.save() for f in files if not f.pk]

            # bulk=False causes Files the File.save() method to be called for
            # each file, including pre_save/post_save hooks.
            self.files.add(*files, bulk=False)

            self.modified_time = datetime.now()

            for job in self.jobs():
                job.modified_time = datetime.now()
                job.save()

            if save:
                self.save()

    @transaction.atomic
    def remove(self, files: Union[File, List[File]], save=True, delete=False):
        """
        Remove a File or Files to the FileSet. Takes a File object or a list
        of Files.

        :param files: A single File object or a list of File objects.
        :type files: File | Sequence[File]
        :param delete: Delete the Files after removing them from this FileSet
                       (doesn't check if other FileSets or database objects still
                        hold a reference to this file, in the case that they are
                        using non-relational JSON blobs)
        :type delete: bool
        :return: None
        :rtype: NoneType
        """
        if not isinstance(files, Sequence):
            files = [files]

        files = unique(files)

        with transaction.atomic():
            # bulk=False causes Files the File.delete() method to be called for
            # each file, including pre_save/post_save hooks.
            self.files.remove(*files, bulk=False)

            if delete:
                [f.delete() for f in files]

            self.modified_time = datetime.now()

            for job in self.jobs():
                job.modified_time = datetime.now()
                job.save()

            if save:
                self.save()

    def get_files(self) -> QuerySet:
        """
        Return all the File objects associated with this FileSet.

        :return: The File object in this FileSet (as a Django QuerySet).
        :rtype: django.models.query.QuerySet(File)
        """
        return self.files.order_by('path', 'name')

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

    def jobs(self):
        return self.jobs_as_input.all().union(self.jobs_as_output.all()).all()


@reversion.register()
class SampleSet(Timestamped, UUIDModel):
    """
    A set of samples for a pipeline run. This often reflects the state of the 'sample cart'
    when setting up a job via the web frontend.

    name - A short friendly name for the sample set.
    samples - A JSON blob representing each 'sample' and the associated URLs or File IDs.
    owner - The User who owns this object.
    """

    name = CharField(max_length=2048, blank=True, null=True)
    owner = ForeignKey(User,
                       blank=True,
                       null=True,
                       on_delete=models.CASCADE,
                       related_name='samplesets')

    samples = JSONField(default=list)

    # saved = BooleanField(default=False)

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

    def from_csv(self, csv_string, header=False, dialect='excel',
                 comment_char='#', save=True):
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

        if isinstance(csv_string, str):
            lines = list(csv.reader(csv_string.splitlines(), dialect=dialect))
        elif isinstance(csv_string, List):
            lines = csv_string

        if header:  # skip header
            lines = lines[1:]

        for line in lines:
            fields = line
            # skip empty lines
            if not fields:
                continue
            sample_name = fields[0].strip()

            if sample_name == '':
                if prev_sample_name:
                    sample_name = prev_sample_name
                else:
                    raise ValueError('First row sample name cannot be blank')

            if sample_name not in samples:
                samples[sample_name] = []

            # TODO: Convert URLs into UUIDs
            # Files may be specified as (existing) UUIDs or URLs.
            # If they are URLs, create (or lookup) associated file objects
            # for that user

            pair = OrderedDict(
                {f'R{n + 1}': file.strip() for n, file in enumerate(fields[1:])})
            samples[sample_name].append(pair)
            prev_sample_name = sample_name

        # We initially create a structure like {sampleName: [{"R1": fileId1, "R2": fileId2}]},
        # Then convert to [{name: sampleName, files: [ ... ]},]
        sample_list = []
        for sample_name, files in samples.items():
            sample_list.append({'name': sample_name, 'files': files})

        self.samples = sample_list
        if save:
            self.save()

    def to_csv(self, newline='\r\n'):
        lines = []
        for sample in self.samples:
            sample_name = sample.get('name')
            for pair in sample.get('files', {}):
                lines.append(','.join([sample_name] + list(pair.values())))

        # TODO: Optionally convert File UUIDs into URLs

        return newline.join(lines)


@reversion.register()
class PipelineRun(Timestamped, UUIDModel):
    owner = ForeignKey(User,
                       blank=True,
                       null=True,
                       on_delete=models.CASCADE,
                       related_name='pipeline_runs')

    # NOTE: This may become a ForeignKey pointing to a Pipeline definition
    #       Currently it's intended to be a pipeline name used as an identifier
    #       (eg, used to run the correct job script, possibly on a suitable
    #        ComputeResource)
    pipeline = CharField(max_length=256, blank=True, null=True)

    sample_set = ForeignKey(SampleSet,
                            blank=True,
                            null=True,
                            on_delete=models.SET_NULL,
                            related_name='pipeline_runs')

    # Sample metadata, keyed by sample name
    # - eg, mapping sample names to conditions
    # {"SampleA": { "conditions": ["wt", "ugly"]},
    #  "SampleB": { "conditions": ["mutant"]} }
    # sample_metadata = JSONField(default=OrderedDict)

    # Parameters specific to the pipeline (eg reference genome)
    params = JSONField(default=OrderedDict)

    # Free-text comment, mostly for users to help keep track of runs.
    description = CharField(max_length=2048, blank=True, null=True)

    def to_json(self):
        # TODO: Convert File UUIDs into URLs here (or internal 'api/v1/file/{file_id}' URLs) ?
        from .serializers import PipelineRunSerializer
        return json.dumps(PipelineRunSerializer(self).data)


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
    owner_field_name = 'created_by'

    token = CharField(db_index=True, max_length=64, blank=False, null=False,
                      default=_generate_access_token_string)
    expiry_time = DateTimeField(blank=True, null=True)
    created_by = ForeignKey(User,
                            blank=True,
                            null=True,
                            on_delete=models.CASCADE,
                            related_name='access_tokens')

    content_type = ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    object_id = CharField(db_index=True, null=True, max_length=24)
    obj = GenericForeignKey('content_type', 'object_id')

    def is_valid(self, target_obj: Union[UUIDModel, str] = None):
        if self.expiry_time is not None and (datetime.now() < self.expiry_time):
            return False

        if isinstance(target_obj, str):
            return self.object_id == target_obj
        if isinstance(target_obj, UUIDModel):
            ct = ContentType.objects.get_for_model(target_obj)
            return self.object_id == target_obj.id and self.content_type == ct
