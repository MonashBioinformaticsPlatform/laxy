from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

# from builtins import (ascii, bytes, chr, dict, filter, hex, input,
#                       int, map, next, oct, open, pow, range, round,
#                       str, super, zip)

from collections import OrderedDict
from datetime import datetime
import uuid
import base64
from django.conf import settings
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import models
from django.core.validators import URLValidator
from django.db.models import Model, CharField, TextField, UUIDField, \
    URLField, ForeignKey, BooleanField, IntegerField, DateTimeField
from django.contrib.auth.models import User
from django.utils import timezone
import reversion
from rest_framework.authtoken.models import Token

from django.db import connection


from .util import generate_uuid, generate_secret_key

if 'postgres' not in settings.DATABASES['default']['ENGINE']:
    from jsonfield import JSONField
else:
    from django.contrib.postgres.fields import JSONField


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Automatically create an Django Rest Framework API Token for every user when
    their User model is first created.

    http://www.django-rest-framework.org/api-guide/authentication/#generating-tokens
    """
    if created:
        Token.objects.create(user=instance)


class URLFieldExtra(URLField):
    schemes = ['http',
               'https',
               'ftp',
               'sftp',
               's3',
               'magnet',
               ]
    default_validators = [URLValidator(schemes=schemes)]


class UserProfile(models.Model):
    user = models.ForeignKey(User, blank=False, related_name='profile')
    # favorite_color = models.CharField(default='2196F3', max_length=6)


class UUIDModel(Model):
    # We don't use the native UUIDField (even though it's more efficient on
    # Postgres) since it makes inspecting the database for the job_id a
    # nuisance.
    # id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Alternative: https://github.com/nebstrebor/django-shortuuidfield ?
    class Meta:
        abstract = True

    id = CharField(primary_key=True,
                   editable=False,
                   max_length=24,
                   default=generate_uuid)

    def uuid(self):
        return self.id


@reversion.register()
class ComputeResource(UUIDModel):
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
    # resource has been decommissioned and won't be available. permananet.
    STATUS_DECOMMISSIONED = 'decommissioned'

    COMPUTE_STATUS_CHOICES = ((STATUS_CREATED, 'object_created'),
                              (STATUS_STARTING, 'starting'),
                              (STATUS_ONLINE, 'online'),
                              (STATUS_ERROR, 'error'),
                              (STATUS_OFFLINE, 'offline'),
                              (STATUS_TERMINATING, 'terminating'),
                              (STATUS_DECOMMISSIONED, 'decommissioned'),
                              )

    status = CharField(max_length=64,
                       choices=COMPUTE_STATUS_CHOICES,
                       default=STATUS_CREATED)

    type = CharField(max_length=255, default='cfncluster')
    host = CharField(max_length=255, blank=True, null=True)
    gateway_server = CharField(max_length=255, blank=True, null=True)
    disposable = BooleanField(default=True)
    name = CharField(max_length=128, blank=True, null=True)
    created_time = DateTimeField(auto_now_add=True)
    modified_time = DateTimeField(auto_now=True)

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


@reversion.register()
class Job(UUIDModel):
    STATUS_CREATED = 'created'
    STATUS_STARTING = 'starting'
    STATUS_RUNNING = 'running'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETE = 'complete'

    JOB_STATUS_CHOICES = ((STATUS_CREATED, 'object_created'),
                          (STATUS_STARTING, 'starting'),
                          (STATUS_RUNNING, 'running'),
                          (STATUS_FAILED, 'failed'),
                          (STATUS_CANCELLED, 'cancelled'),
                          (STATUS_COMPLETE, 'complete'),
                          )

    owner = ForeignKey(User, related_name='jobs')
    secret = CharField(max_length=255,
                       blank=True,
                       null=True,
                       default=generate_secret_key)
    status = CharField(max_length=64,
                       choices=JOB_STATUS_CHOICES,
                       default=STATUS_CREATED)
    exit_code = IntegerField(blank=True, null=True)
    data_origin = URLFieldExtra(max_length=255)
    params = JSONField()  # django-jsonfield or native Postgres

    compute_resource = ForeignKey(ComputeResource,
                                  blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL,
                                  related_name='jobs')

    created_time = DateTimeField(auto_now_add=True)
    modified_time = DateTimeField(auto_now=True)
    completed_time = DateTimeField(blank=True, null=True)

    @property
    def done(self):
        """
        Returns True if the job has finished, either successfully
        or unsucessfully.

        :return: True if job is no longer running.
        :rtype: bool
        """
        return (self.status == Job.STATUS_COMPLETE or
                self.status == Job.STATUS_CANCELLED or
                self.status == Job.STATUS_FAILED)

    def _generate_cluster_stack_name(self):
        """
        Generate a name for a compute cluster resource.

        Since this becomes an AWS (or OpenStack?) Stack name via CloudFormation
        it can only contain alphanumeric characters (upper and lower) and hyphens
        and cannot be longer than 128 characters.

        :param job: A Job instance (with ComputeResource assigned)
        :type job: Job
        :return: A cluster ID to use as the stack name.
        :rtype: str
        """
        return 'cluster-%s----%s' % (self.compute_resource.id, self.id)

    def save(self, *args, **kwargs):
        super(Job, self).save(*args, **kwargs)
        compute = self.compute_resource
        if compute and compute.disposable and not compute.stack_name:
            compute.stack_name = self._generate_cluster_stack_name()
            compute.save()


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
        if instance.status == Job.STATUS_COMPLETE and \
                obj.status != Job.STATUS_COMPLETE and \
                not obj.completed_time:
            instance.completed_time = datetime.now()


@reversion.register()
class File(UUIDModel):
    """
    File model.

    name - The file name.
    url - A URI describing the (cached) location of the input file.
    origin - A URI describing the original location of the file, where we
             initially downloaded it from.
    """

    # The filename. Equivalent to path.basename(location) in most cases
    name = CharField(max_length=2048)
    # Any hash supported by hashlib, and xxhash
    checksum = CharField(max_length=255)  # md5:11fca9c1f654078189ad040b1132654c
    owner = ForeignKey(User, related_name='files')
    # The URL to the file. Could be file://, https://, s3://, sftp://
    location = URLFieldExtra(max_length=2048)
    origin = URLFieldExtra(max_length=2048)
    job = ForeignKey(Job,
                     on_delete=models.CASCADE,
                     related_name='files')

    def to_dict(self):
        return OrderedDict(name=self.name,
                           origin=self.origin,
                           location=self.location,
                           job=self.job.uuid())


@reversion.register()
class FileSet(UUIDModel):
    """
    A set of files. Might be used to represent a directory.

    name - The set name (eg directory name)
    files - The files in this FileSet.

    """
    name = CharField(max_length=2048)
    # TODO: Using ManyToManyField here is going to create lots of intermediate
    # tables. A better option here might just be a list in a JSONField, or a
    # Postgres specific ArrayField
    files = models.ManyToManyField(File)
