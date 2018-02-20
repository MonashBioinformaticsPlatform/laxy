# from __future__ import (absolute_import, division,
#                         print_function, unicode_literals)

# from builtins import (ascii, bytes, chr, dict, filter, hex, input,
#                       int, map, next, oct, open, pow, range, round,
#                       str, super, zip)

from typing import List
from collections import OrderedDict, Sequence
from datetime import datetime
import csv
import uuid
from pathlib import Path
from urllib.parse import urlparse
import base64
from basehash import base62
import xxhash
from django.conf import settings
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import models, transaction
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db.models import Model, CharField, TextField, UUIDField, \
    URLField, ForeignKey, BooleanField, IntegerField, DateTimeField
from django.contrib.auth.models import User
from django.utils import timezone
import reversion
from rest_framework.authtoken.models import Token

from django.db import connection

from .cfncluster import generate_cluster_stack_name
from .util import generate_uuid, generate_secret_key

if 'postgres' not in settings.DATABASES['default']['ENGINE']:
    from jsonfield import JSONField
else:
    from django.contrib.postgres.fields import JSONField


def unique(l):
    return list(set(l))


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


class UserProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             blank=False,
                             related_name='profile')
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

    # type = CharField(max_length=255, blank=True)
    '''
    The host `type` is used for logic around how the host is used 
    (deployment, job submission, decommissioning).
    eg, values might be 'cfncluster', 'ssh' or 'slurm'.
    
    WIP: This was historically only ever 'cfncluster' in the original prototype.
    We will re-enable it when it actually has a use.
    Maybe this could be better expressed as a set of tags, or a name
    corresponding to a host management utility class (plugable) for each 
    type of host.
    '''

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
    """
    Represents a processing job (typically a long running remote job managed
    by a Celery task queue).
    """
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

    owner = ForeignKey(User,
                       on_delete=models.SET_NULL,
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
    # django-jsonfield or native Postgres
    params = JSONField(default=OrderedDict)
    # jsonfield or native Postgres
    # params = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})

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

    created_time = DateTimeField(auto_now_add=True)
    modified_time = DateTimeField(auto_now=True)
    completed_time = DateTimeField(blank=True, null=True)

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

    def save(self, *args, **kwargs):
        super(Job, self).save(*args, **kwargs)

        # For a single-use ('disposable') ComputeResource associated with a
        # single job, we automatically name the resource based on the associated
        # job UUID.
        compute = self.compute_resource
        if compute and compute.disposable and not compute.name:
            compute.name = generate_cluster_stack_name(self)
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
    _name = CharField(db_column='name', max_length=2048, blank=True, null=True)
    # Any hash supported by hashlib, and xxhash, in the format:
    # hashtype:th3actualh4shits3lf
    # eg: md5:11fca9c1f654078189ad040b1132654c
    checksum = CharField(max_length=255, blank=True, null=True)
    owner = ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    # The URL to the file. Could be file://, https://, s3://, sftp://
    location = URLField(max_length=2048, blank=False, null=False,
                        validators=[URIValidator()])
    # origin = URLFieldExtra(max_length=2048)

    metadata = JSONField(default=OrderedDict)

    # metadata = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})

    # There is no direct link from File->Job, instead we use FileSet->Job.
    # This way, Files represent a single unique file (on disk, or at a URL),
    # and FileSets can represent a set of files used
    # as input/output of a Job.
    # job = ForeignKey(Job,
    #                  on_delete=models.CASCADE,
    #                  related_name='files')

    @property
    def name(self):
        if self._name:
            return self._name
        else:
            fn = Path(urlparse(self.location).path).name
            # TODO: If fn is empty, we could still grab the filename
            #       from the utils.find_filename_and_size_from_url,
            #       (only upon creation, or when location changes)
            return fn

    @name.setter
    def name(self, value):
        self._name = value

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
    owner = ForeignKey(User,
                       on_delete=models.CASCADE,
                       related_name='filesets')

    # Using a ManyToManyField here is going to create lots of intermediate
    # tables, so we just use a JSONField instead
    # (or maybe Postgres ArrayField, Django-MySQL ListCharField ?)
    # files = models.ManyToManyField(File)

    # a list of File ids eg ['2VSd4mZvmYX0OXw07dGfnV', '3XSd4mZvmYX0OXw07dGfmZ']
    files = JSONField(default=list)

    # TODO: a list of FileSet ids (effectively like subdirectories) ?
    # filesets = JSONField(default=list)

    job = ForeignKey(Job,
                     on_delete=models.CASCADE,
                     related_name='files',
                     null=True,
                     blank=True)

    @transaction.atomic
    def add(self, files, save=True):
        """
        Add a File or Files to the FileSet. Takes a File object or it's ID,
        or a list of Files or IDs.

        :param file: The File object or it's ID, or a list of these.
        :type file: File | str | Sequence[File] | Sequence[str]
        :return: None
        :rtype: NoneType
        """
        if isinstance(files, str):
            files = [files]
        elif isinstance(files, File):
            if save:
                files.save()
            files = [files.id]
        elif isinstance(files, Sequence):
            _files = []
            for f in files:
                if isinstance(f, str):
                    _files.append(f)
                elif isinstance(f, File):
                    _files.append(f.id)
                    if save:
                        f.save()
                else:
                    raise ValueError(
                        "You must provide a File, a list or Files, "
                        "a string ID or a list of string IDs")
            files = _files
        # if isinstance(files, Sequence) and \
        #    all([isinstance(f, str) for f in files]):
        #     files = files
        # if isinstance(files, Sequence) and \
        #    all([isinstance(f, File) for f in files]):
        #     files = [f.id for f in files]
        else:
            raise ValueError("You must provide a File, a list or Files, "
                             "a string ID or a list of string IDs")

        # we ensure all IDs in the list are unique
        files = unique(files)

        if File.objects.filter(id__in=files).count() != len(files):
            raise ValueError("One or more File IDs do not exist.")

        self.files.extend(files)
        self.files = sorted(unique(self.files))  # remove any duplicates
        if save:
            self.save()

    @transaction.atomic
    def remove(self, files, save=True, delete=False):
        if isinstance(files, str) or not isinstance(files, Sequence):
            files = [files]

        for f in files:
            if isinstance(f, File):
                self.files.remove(f.id)
            elif isinstance(f, str):
                self.files.remove(f)

            if delete:
                f = File.objects.get(id=getattr(f, 'id', str(f)))
                f.delete()

        if save:
            self.save()

    def get_files(self):
        """
        Return all the File objects associated with this FileSet.

        :return: The File object in this FileSet (as a Django QuerySet).
        :rtype: django.models.query.QuerySet(File)
        """
        return File.objects.filter(id__in=self.files)


@reversion.register()
class SampleSet(UUIDModel):
    """
    A set of samples for a pipeline run. Might be used to represent a directory.

    name - The set name (eg directory name)
    samples - A JSON blob representing each 'sample' and the associated Files.
    owner - The User who owns this object.
    """

    name = CharField(max_length=2048)
    owner = ForeignKey(User,
                       on_delete=models.CASCADE,
                       related_name='samplesets')
    samples = JSONField(default=OrderedDict)

    # 'samples' is a dictionary keyed by sample name, with a list of files grouped by
    # merge_group and pair (a merge_group could be a set of equivalent lanes the sample
    # was split accross, or a technical replicate):
    #
    # Equivalent samples (technical replicates) in different lanes can be merged -
    # they could also be thought of as split FASTQ files.

    # Structure:
    # {sampleName, [[R1_lane1, R2_lane1], [R1_lane2, R2_lane2]]}

    # A single 'sampleName' actually corresponds to a Sample+Condition+BiologicalReplicate.

    # for two samples (R1, R2 paired end) split across two lanes, using File UUIDs
    #
    # {"sample_wildtype": [{"R1": "2VSd4mZvmYX0OXw07dGfnV", "R2: "3XSd4mZvmYX0OXw07dGfmZ"},
    #                      {"R1": "Toopini9iPaenooghaquee", "R2": "Einanoohiew9ungoh3yiev"}],
    #  "sample_mutant":   [{"R1": "zoo7eiPhaiwion6ohniek3", "R2": "ieshiePahdie0ahxooSaed"],
    #                      ["R1": "nahFoogheiChae5de1iey3", "R2": "Dae7leiZoo8fiesheech5s"]],}
    #
    # We would merge the R1s together for a sample and the R2s together for a sample:
    # eg, merge "2VSd4mZvmYX0OXw07dGfnV" with "Toopini9iPaenooghaquee"
    #     and   "3XSd4mZvmYX0OXw07dGfmZ" with "Einanoohiew9ungoh3yiev"
    # ..etc.. as technical replicates

    def from_csv(self, csv_string, header=False, dialect='excel', comment_char='#', save=True):
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

            pair = OrderedDict({f'R{n+1}': file.strip()
                                for n, file in enumerate(fields[1:])})
            samples[sample_name].append(pair)
            prev_sample_name = sample_name

        self.samples = samples
        if save:
            self.save()

    def to_csv(self, newline='\r\n'):
        lines = []
        for sample_name, pairs in self.samples.items():
            for pair in pairs:
                lines.append(','.join([sample_name] + list(pair.values())))

        return newline.join(lines)
