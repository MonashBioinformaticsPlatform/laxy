from typing import Union, Sequence, List
import os
import json
from pathlib import Path
from base64 import urlsafe_b64encode
from urllib.parse import urlparse, urlsplit, urlunsplit

import pymmh3 as mmh3

from datetime import datetime, timedelta

from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from guardian.models import UserObjectPermission, GroupObjectPermission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.migrations.recorder import MigrationRecorder
import django.forms
from django.urls import reverse
from humanize import naturalsize
from django.contrib.humanize.templatetags import humanize

from django.template.defaultfilters import truncatechars
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from reversion.admin import VersionAdmin

from django_object_actions import DjangoObjectActions, takes_instance_or_queryset

from laxy_backend.tasks import job as job_tasks
from laxy_backend.tasks import file as file_tasks

from .models import (
    Job,
    ComputeResource,
    File,
    FileLocation,
    FileSet,
    SampleCart,
    PipelineRun,
    Pipeline,
    EventLog,
    SystemStatus,
    UserProfile,
    AccessToken,
    URIValidator,
)
from .views import get_abs_backend_url, JobCreate
from .jwt_helpers import get_jwt_user_header_str

from laxy_backend.models import get_compute_resource_for_location
from laxy_backend.util import split_laxy_sftp_url

import logging

logger = logging.getLogger(__name__)

User = get_user_model()


def truncate_middle(text: str, middle="…", length=77, end=8) -> str:
    """
    Truncates the 'middle' of a string, leaving `end` characters at the end intact,
    and replacing some characters in the middle with an ellipsis.

    :param text:
    :type text:
    :param middle:
    :type middle:
    :param length:
    :type length:
    :param end:
    :type end:
    :return:
    :rtype:
    """
    if len(text) > length:
        return text[: (length - 8)] + middle + text[(-1 * end) :]
    else:
        return text


def url_to_cache_key(url: str, strip_fragment: bool = True) -> str:
    """
    Generate a cache key for a URL using the same method as laxydl.

    A URL hashed with Murmur3 and base64 encoded into a constant length (22 character)
    string. We use Murmur3 since it is supposed to have very few collisions for short
    strings.

    :param url: The URL to generate a cache key for
    :param strip_fragment: Whether to remove URL fragments before hashing
    :return: A cache key string
    """
    if strip_fragment:
        urlparts = list(urlsplit(url))
        urlparts[4] = ""  # remove hash fragment
        url = urlunsplit(urlparts)

    return (
        urlsafe_b64encode(mmh3.hash128(url).to_bytes(16, byteorder="big", signed=False))
        .decode("ascii")
        .rstrip("=")
    )


def get_urls_from_job_params(job_params: dict) -> list:
    """
    Extract URLs from job parameters that were downloaded.
    
    :param job_params: The job's params field
    :return: List of URLs that were downloaded
    """
    urls = []
    
    # Check if there's a fetch_files array in the params
    if isinstance(job_params, dict):
        # Direct fetch_files in params
        fetch_files = job_params.get("fetch_files", [])
        if fetch_files:
            for file_info in fetch_files:
                if isinstance(file_info, dict) and "location" in file_info:
                    urls.append(file_info["location"])
        
        # Check nested params structure
        nested_params = job_params.get("params", {})
        if isinstance(nested_params, dict):
            fetch_files = nested_params.get("fetch_files", [])
            if fetch_files:
                for file_info in fetch_files:
                    if isinstance(file_info, dict) and "location" in file_info:
                        urls.append(file_info["location"])
    
    return urls


class Timestamped:
    list_display = (
        "uuid",
        "created",
        "modified",
    )
    ordering = (
        "-created_time",
        "-modified_time",
    )

    def uuid(self, obj):
        return "%s" % obj.uuid()

    def created(self, obj):
        return humanize.naturaltime(obj.created_time)

    def modified(self, obj):
        return humanize.naturaltime(obj.modified_time)


class MigrationAdmin(admin.ModelAdmin):
    ordering = ("-applied",)
    list_display = ("app", "name", "applied")
    readonly_fields = ("app", "name", "applied")


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


class LaxyUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
    )
    list_select_related = ("profile",)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(LaxyUserAdmin, self).get_inline_instances(request, obj)


class UserProfileAdmin(admin.ModelAdmin):
    pass


class GuardianUserObjectPermissionAdmin(admin.ModelAdmin):
    """
    Manage django-guardian object level permissions directly (user-level) in Django admin.
    """

    pass


class GuardianGroupObjectPermissionAdmin(admin.ModelAdmin):
    """
    Manage django-guardian object level permissions directly (group-level) in Django admin.
    """

    pass


class ComputeResourceAdmin(Timestamped, VersionAdmin):
    list_display = ("uuid", "name", "address", "priority", "created", "status_html")
    search_fields = (
        "id",
        "name",
        "host",
        "status",
    )
    list_filter = ("status",)
    ordering = (
        "-priority",
        "-created_time",
    )

    color_mappings = {
        ComputeResource.STATUS_ONLINE: "green",
        ComputeResource.STATUS_ERROR: "red",
        ComputeResource.STATUS_STARTING: "orange",
        ComputeResource.STATUS_TERMINATING: "orange",
    }

    def status_html(self, obj):
        return format_html(
            '<span style="color: {};"><strong>{}</strong></span>',
            self.color_mappings.get(obj.status, "black"),
            obj.get_status_display(),
        )

    def address(self, obj):
        if obj.status == ComputeResource.STATUS_ONLINE:
            return obj.host
        else:
            return ""


def async_copy_files(files, dst_compute_id: Union[None, str] = None):
    """
    Starts async (celery) copy tasks for a set of files to a destination ComputeResource (by ID).

    Returns a list of file IDs that failed immediately (some tasks may start but fail after some time, 
    these won't be included in the failed list). 
    """

    failed = []
    for file in files:
        if file.location is None:
            logger.error(
                f"File {file.id} has no location. Skipping copy_to_archive for this file."
            )
            continue

        src_compute, job, path, filename = split_laxy_sftp_url(
            file.location, to_objects=True
        )
        src_prefix = f"laxy+sftp://{src_compute.id}/"

        if dst_compute_id is None:
            if job.compute_resource.archive_host:
                dst_compute_id = job.compute_resource.archive_host.id
            else:
                failed.append(file.id)

        dst_prefix = f"laxy+sftp://{dst_compute_id}/"
        from_location = str(file.location)
        to_location = str(file.location).replace(src_prefix, dst_prefix)

        task_data = dict(
            file_id=file.id,
            from_location=from_location,
            to_location=to_location,
            clobber=True,
        )

        if from_location != to_location:
            result = file_tasks.copy_file_task.apply_async(args=(task_data,))

            if result.failed():
                failed.append(file.id)

    return failed


class JobAdmin(Timestamped, VersionAdmin):
    list_display = (
        "uuid",
        "created",
        "completed",
        "expires",
        "_pipeline",
        "_compute_resource",
        "_owner_email",
        "_status",
        "_size",
    )
    ordering = ("-created_time", "-completed_time", "-modified_time", "-expiry_time")
    search_fields = (
        "id",
        "status",
        "remote_id",
        "owner_id__exact",
        "owner__email__exact",
    )
    list_filter = (
        "status",
        "expired",
    )
    actions = (
        "index_remote_files",
        "expire_job",
        "estimate_job_tarball_size",
        "verify",
        "copy_to_archive",
        "move_job_files_to_archive",
        "bulk_rsync_job",
        "rerun_job",
        "delete_cached_downloads",
    )

    color_mappings = {
        Job.STATUS_FAILED: "red",
        Job.STATUS_CANCELLED: "red",
        Job.STATUS_RUNNING: "green",
    }

    def completed(self, obj: Job):
        return humanize.naturaltime(obj.completed_time)

    def expires(self, obj: Job):
        return humanize.naturaltime(obj.expiry_time)

    def _pipeline(self, obj: Job):
        pipeline = obj.params.get("pipeline", None)
        pipeline_version = obj.params.get("params", {}).get("pipeline_version", None)
        if pipeline is not None:
            return format_html(f"{pipeline} ({pipeline_version})")
        return format_html("<i>???</i>")

    def _compute_resource(self, obj: Job):
        c = obj.compute_resource
        if c is not None:
            return format_html("%s (%s)" % (c.name, c.id))
        else:
            return ""

    def _status(self, obj: Job):
        return format_html(
            '<span style="color: {};"><strong>{}</strong></span>',
            self.color_mappings.get(obj.status, "black"),
            obj.get_status_display(),
        )

    def _size(self, obj: Job):
        size = obj.params.get("tarball_size", None)
        if size is not None:
            return format_html(naturalsize(size))
        return format_html("<i>unknown</i>")

    def _owner_email(self, obj: Job):
        if obj.owner:
            ct = ContentType.objects.get_for_model(obj.owner)
            user_url = reverse(
                "admin:%s_%s_change" % (ct.app_label, ct.model), args=(obj.owner.id,)
            )
            return format_html(
                '<a href="{}">{} ({})</a>', user_url, obj.owner.email, obj.owner.id
            )
        return ""

    @takes_instance_or_queryset
    def index_remote_files(self, request, queryset):
        failed = []
        for obj in queryset:
            task_data = dict(job_id=obj.id, clobber=False)
            result = job_tasks.index_remote_files.apply_async(args=(task_data,))
            if result.failed():
                failed.append(obj.id)
        if not failed:
            self.message_user(request, "Indexing !")
        else:
            self.message_user(request, "Errors trying to index %s" % ",".join(failed))

    index_remote_files.short_description = "Index job files"

    @takes_instance_or_queryset
    def estimate_job_tarball_size(self, request, queryset):
        failed = []
        for obj in queryset:
            task_data = dict(job_id=obj.id)
            result = job_tasks.estimate_job_tarball_size.apply_async(args=(task_data,))
            if result.failed():
                failed.append(obj.id)
        if not failed:
            self.message_user(request, "Starting estimate_job_tarball_size task(s) !")
        else:
            self.message_user(
                request,
                "Errors trying to estimate tarball size for %s" % ",".join(failed),
            )

    estimate_job_tarball_size.short_description = "Estimate tarball size"

    @takes_instance_or_queryset
    def expire_job(self, request, queryset):
        failed = []
        for obj in queryset:
            task_data = dict(job_id=obj.id, ttl=0)
            obj.expiry_time = timezone.now() - timedelta(seconds=5)
            obj.save()
            result = job_tasks.expire_old_job.apply_async(args=(task_data,))
            if result.failed():
                failed.append(obj.id)
        if not failed:
            self.message_user(request, f"Expiring job: {obj.id}")
        else:
            self.message_user(request, "Errors trying to expire %s" % ",".join(failed))

    expire_job.short_description = "Expire job (delete large files)"

    @takes_instance_or_queryset
    def verify(self, request, queryset):
        failed = []
        for obj in queryset:
            for f in obj.get_files():
                for loc in f.locations.all():
                    task_data = dict(file_id=f.id, filelocation_id=loc.id)
                    result = file_tasks.verify_task.apply_async(args=(task_data,))
                    if result.failed():
                        failed.append(loc.id)

        if not failed:
            self.message_user(request, "Verifying !")
        else:
            self.message_user(
                request,
                "Errors trying to launch verify tasks for %d file locations (%s)"
                % (len(failed), ",".join(failed)),
            )

    verify.short_description = "Verify job files (all locations)"

    @takes_instance_or_queryset
    def copy_to_archive(self, request, queryset):
        failed = []
        for job in queryset:
            archive_host = job.compute_resource.archive_host
            if archive_host is None:
                self.message_user(
                    request,
                    f"Unable to copy job {job.id}, ComputeResource "
                    f"{job.compute_resource.id} has no archive_host !",
                )
                return

            dst_compute = archive_host.id

            failed = async_copy_files(job.get_files(), dst_compute)

            if not failed:
                self.message_user(request, "Copying !")
            else:
                self.message_user(
                    request, "Errors trying to copy %s" % ",".join(failed)
                )

    copy_to_archive.short_description = "Copy files to archive location"

    @takes_instance_or_queryset
    def move_job_files_to_archive(self, request, queryset):
        failed = []
        for job in queryset:
            task_data = dict(job_id=job.id)
            result = job_tasks.move_job_files_to_archive_task.apply_async(
                args=(task_data,)
            )
            if result.failed():
                failed.append(job.id)

        if not failed:
            self.message_user(request, "Bulk moving now !")
        else:
            self.message_user(
                request, "Errors trying to initiate transfer of %s" % ",".join(failed)
            )

    move_job_files_to_archive.short_description = "Move job files to archive host"

    @takes_instance_or_queryset
    def bulk_rsync_job(self, request, queryset):
        failed = []
        for job in queryset:
            task_data = dict(job_id=job.id)
            result = job_tasks.bulk_move_job_rsync.apply_async(args=(task_data,))
            if result.failed():
                failed.append(job.id)

        if not failed:
            self.message_user(request, "Moving jobs to archive (bulk rsync) !")
        else:
            self.message_user(
                request, "Errors trying to initiate transfer of %s" % ",".join(failed)
            )

    bulk_rsync_job.short_description = "Bulk move (rsync) job(s) to archive location"

    @takes_instance_or_queryset
    def rerun_job(self, request, queryset):
        for job in queryset:
            job_id = job.id

            callback_url = get_abs_backend_url(
                reverse("laxy_backend:job", args=[job.id])  # , request
            )

            job_event_url = get_abs_backend_url(
                reverse("laxy_backend:create_job_eventlog", args=[job.id])  # , request
            )

            job_file_bulk_url = get_abs_backend_url(
                reverse("laxy_backend:job_file_bulk", args=[job_id])  # , request
            )

            # callback_auth_header = get_jwt_user_header_str(job.owner.username)

            result = JobCreate().start_job(
                job,
                callback_url=callback_url,
                job_event_url=job_event_url,
                job_file_bulk_url=job_file_bulk_url,
                # callback_auth_header=callback_auth_header,
            )

    rerun_job.short_description = "Restart job in-place (blindly re-runs run_job.sh)"

    @takes_instance_or_queryset
    def delete_cached_downloads(self, request, queryset):
        """
        Delete cached downloads for selected jobs.
        Finds the cache directory from the compute resource's extra settings,
        generates cache keys for URLs in the job's fetch_files, and deletes
        the cached files if they exist on the remote compute resource.
        """
        failed_jobs = []
        deleted_files = []
        not_found_files = []
        total_deleted = 0
        total_processed = 0
        
        for job in queryset:
            total_processed += 1
            try:
                # Get the compute resource
                compute_resource = job.compute_resource
                if not compute_resource:
                    failed_jobs.append(f"{job.id} (no compute resource)")
                    continue
                
                # Check if compute resource is available
                if not compute_resource.available:
                    failed_jobs.append(f"{job.id} (compute resource not available: {compute_resource.status})")
                    continue
                
                # Get cache directory from compute resource extra settings
                cache_dir = compute_resource.extra.get("cache_dir")
                if not cache_dir:
                    failed_jobs.append(f"{job.id} (no cache_dir in compute resource extra settings)")
                    continue
                
                # Construct the downloads cache path on the remote host
                downloads_cache_path = f"{cache_dir}/downloads"
                
                # Get URLs from job parameters
                urls = get_urls_from_job_params(job.params)
                if not urls:
                    failed_jobs.append(f"{job.id} (no fetch_files found in job parameters)")
                    continue
                
                # Use SSH to delete cached files for each URL
                job_deleted = 0
                job_not_found = 0
                with compute_resource.ssh_client() as ssh_client:
                    for url in urls:
                        cache_key = url_to_cache_key(url)
                        
                        # Validate cache key to prevent path traversal
                        if (not cache_key 
                            or '/' in cache_key 
                            or '..' in cache_key):
                            error_msg = f"Invalid cache key generated for URL: url={url}, cache_key={cache_key}"
                            logger.error(f"Admin action - delete_cached_downloads: {error_msg}")
                            failed_jobs.append(f"{job.id} ({error_msg})")
                            continue
                        
                        remote_cached_file_path = f"{downloads_cache_path}/{cache_key}"
                        
                        # Check if file exists and delete it
                        stdin, stdout, stderr = ssh_client.exec_command(f"test -f '{remote_cached_file_path}' && rm -f '{remote_cached_file_path}' && echo 'deleted' || echo 'not_found'")
                        result = stdout.read().decode().strip()
                        stderr_output = stderr.read().decode().strip()
                        
                        if result == "deleted":
                            job_deleted += 1
                            deleted_files.append(f"{job.id}: {url}")
                            logger.info(f"Admin action - delete_cached_downloads: Deleted cached file {remote_cached_file_path} for job {job.id}")
                        elif result == "not_found":
                            job_not_found += 1
                            not_found_files.append(f"{job.id}: {url}")
                            logger.debug(f"Admin action - delete_cached_downloads: Cached file {remote_cached_file_path} not found for job {job.id}")
                        else:
                            error_msg = f"Failed to delete cached file {remote_cached_file_path}: {stderr_output}"
                            logger.error(f"Admin action - delete_cached_downloads: {error_msg}")
                            failed_jobs.append(f"{job.id} ({error_msg})")
                
                total_deleted += job_deleted
                
                if job_deleted > 0:
                    logger.info(f"Admin action - delete_cached_downloads: Deleted {job_deleted} cached files for job {job.id}")
                
                # Show job-specific results
                if job_deleted > 0:
                    self.message_user(
                        request,
                        f"Job {job.id}: Deleted {job_deleted} cached files"
                    )
                
                if job_not_found > 0:
                    self.message_user(
                        request,
                        f"Job {job.id}: {job_not_found} cached files not found (may have been already deleted)",
                        level="WARNING"
                    )
                
            except Exception as e:
                error_msg = f"Error processing job {job.id}: {str(e)}"
                logger.error(f"Admin action - delete_cached_downloads: {error_msg}")
                failed_jobs.append(f"{job.id} ({error_msg})")
        
        # Show summary results to user
        if not_found_files:
            self.message_user(
                request,
                f"Summary: {len(not_found_files)} cached files were not found (may have been already deleted).",
                level="WARNING"
            )
        
        if failed_jobs:
            self.message_user(
                request,
                f"Summary: Failed to process {len(failed_jobs)} jobs due to configuration or connection issues: {', '.join(failed_jobs)}",
                level="ERROR"
            )
        
        if total_processed > 0 and total_deleted == 0 and len(failed_jobs) == 0:
            # Get the first job's compute resource info for the message
            first_job = queryset.first()
            if first_job and first_job.compute_resource:
                cache_dir = first_job.compute_resource.extra.get("cache_dir", "not configured")
                downloads_cache_path = f"{cache_dir}/downloads"
                compute_name = first_job.compute_resource.name or first_job.compute_resource.id
                path_info = f"({compute_name}:{downloads_cache_path})"
            else:
                path_info = "(no compute resource)"
            
            self.message_user(
                request,
                f"No cached files were found to delete for {total_processed} jobs. This may indicate that the cache directory is not configured correctly or the files have already been deleted. Expected path: {path_info}",
                level="WARNING"
            )

    delete_cached_downloads.short_description = "Delete cached downloads"


def do_nothing_validator(value):
    return None


class FileLocationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file",
        "default",
        "_url",
    )
    # raw_id_fields = ('file',)
    readonly_fields = (
        "url",
        "file",
    )
    actions = ("verify",)
    ordering = ("-default",)
    search_fields = (
        "id",
        "url",
        "file__id",
    )

    def _url(self, obj):
        return format_html(
            '<a href="{}">{}</a>', obj.url, truncate_middle(obj.url, end=32)
        )

    @takes_instance_or_queryset
    def verify(self, request, queryset):
        failed = []
        for obj in queryset:
            task_data = dict(file_id=obj.file.id, location=obj.url)
            result = file_tasks.verify_task.apply_async(args=(task_data,))
            if result.failed():
                failed.append(obj.id)
        if not failed:
            self.message_user(request, "Verifying !")
        else:
            self.message_user(
                request,
                "Errors trying to verify %d files (%s)"
                % (len(failed), ",".join(failed)),
            )

    verify.short_description = "Verify file checksum"


class FileLocationAdminForm(django.forms.ModelForm):
    class Meta:
        model = FileLocation
        fields = "__all__"

    url = django.forms.CharField(max_length=2048, validators=[URIValidator()])


class FileLocationsInline(admin.TabularInline):
    model = FileLocation
    readonly_fields = (
        "id",
        "default",
        "url",
    )
    fields = (
        "id",
        "default",
        "url",
    )
    ordering = ("-default",)
    can_delete = False
    verbose_name_plural = "File Locations"
    fk_name = "file"
    extra = 0


class FileAdminForm(django.forms.ModelForm):
    class Meta:
        model = File
        fields = "__all__"

    location = django.forms.CharField(max_length=2048, validators=[URIValidator()])


class FileAdmin(Timestamped, VersionAdmin):
    list_display = ("uuid", "_path", "_name", "location", "created", "modified")
    readonly_fields = ("location",)
    ordering = (
        "-created_time",
        "-modified_time",
    )
    search_fields = (
        "id",
        "path",
        "name",
        "locations__url__contains",
    )
    inlines = (FileLocationsInline,)
    actions = (
        "delete_real_file",
        "fix_metadata",
        "verify",
        "copy_to_archive",
    )
    form = FileAdminForm

    truncate_to = 32

    def _path(self, obj):
        return truncatechars(obj.path, self.truncate_to)

    def _name(self, obj):
        return truncatechars(obj.name, self.truncate_to)

    def location(self, obj):
        url = reverse(
            "laxy_backend:file_download",
            kwargs={"uuid": obj.uuid(), "filename": obj.name},
        )
        return format_html(
            '<a href="{}">{}</a>', url, truncatechars(obj.name, self.truncate_to)
        )

    @takes_instance_or_queryset
    def fix_metadata(self, request, queryset):
        """
        In the (rare) case that a set of Files end up with non-JSON data in the metadata field,
        nuke all those and replace with an empty JSON object.

        This is more for cleaning up when something unexpected occurred (since Postgres JSONB appears
        to still allow non-JSON strings .. :/) and shouldn't replace data migrations if (for instance) the
        File.metadata field JSON shape/schema changed.
        """
        count = 0
        last_msg = ""
        for obj in queryset:
            if isinstance(obj.metadata, str):
                obj.metadata = dict()
                obj.save()
                count += 1
                last = f" (last was for File {obj.id})"
        self.message_user(request, f"Fix {count} metadata fields{last_msg}")

    fix_metadata.short_description = "Fix invalid file metadata"

    @takes_instance_or_queryset
    def verify(self, request, queryset):
        failed = []
        for obj in queryset:
            for loc in obj.locations.all():
                task_data = dict(file_id=obj.id, filelocation_id=loc.id)
                result = file_tasks.verify_task.apply_async(args=(task_data,))
                if result.failed():
                    failed.append(loc.id)

        if not failed:
            self.message_user(request, "Verifying !")
        else:
            self.message_user(
                request, "Errors trying to run verify task for %s" % ",".join(failed)
            )

    verify.short_description = "Verify file (all locations)"

    # TODO: This should be refactored alongside the equivalent function on JobAdmin
    #       to used common code
    @takes_instance_or_queryset
    def copy_to_archive(self, request, queryset):
        failed = []
        failed = async_copy_files(queryset)

        if not failed:
            self.message_user(request, "Copying !")
        else:
            self.message_user(request, "Errors trying to ingest %s" % ",".join(failed))

    copy_to_archive.short_description = "Copy file to archive location"

    def delete_real_file(self, request, queryset):
        failed = []

        for f in queryset:
            try:
                f.delete_file()
            except BaseException as ex:
                failed.append(f.id)

        if not failed:
            self.message_user(request, "Deleting !")
        else:
            self.message_user(request, "Errors trying to delete %s" % ",".join(failed))

    delete_real_file.short_description = "Delete real file at all locations"


class JobInputFilesInline(admin.TabularInline):
    model = Job
    readonly_fields = (
        "id",
        "status",
        "owner",
        "completed_time",
    )
    fields = (
        "id",
        "status",
        "owner",
        "completed_time",
    )
    can_delete = False
    verbose_name_plural = "Associated Job (as input FileSet)"
    fk_name = "input_files"
    extra = 0


class JobOutputFilesInline(admin.TabularInline):
    model = Job
    readonly_fields = (
        "id",
        "status",
        "owner",
        "completed_time",
    )
    fields = (
        "id",
        "status",
        "owner",
        "completed_time",
    )
    can_delete = False
    verbose_name_plural = "Associated Job (as output FileSet)"
    fk_name = "output_files"
    extra = 0


class FilesInline(admin.TabularInline):
    model = File
    readonly_fields = (
        "id",
        "locations_list",
    )
    fields = (
        "id",
        "path",
        "name",
        "locations_list",
        "type_tags",
    )
    ordering = (
        "path",
        "name",
    )
    can_delete = False
    verbose_name_plural = "Files"
    fk_name = "fileset"
    extra = 0

    def locations_list(self, file):
        return format_html("<br>".join([l.url for l in file.locations.all()]))


class FileSetAdmin(Timestamped, VersionAdmin):
    list_display = ("uuid", "path", "name", "created", "modified")
    ordering = (
        "-created_time",
        "-modified_time",
    )
    search_fields = (
        "id",
        "name",
        "path",
    )
    inlines = (
        JobInputFilesInline,
        JobOutputFilesInline,
        FilesInline,
    )


class SampleCartAdmin(Timestamped, VersionAdmin):
    pass


class PipelineRunAdmin(Timestamped, VersionAdmin):
    pass


class PipelineAdmin(GuardedModelAdmin):
    ordering = ("name",)
    list_filter = (
        "name",
        "public",
        "owner",
    )
    list_display = (
        "name",
        "uuid",
        "public",
        "owner",
    )
    search_fields = (
        "id",
        "name",
        "owner",
    )


class EventLogAdmin(admin.ModelAdmin):
    ordering = ("-timestamp",)
    raw_id_fields = ("user",)
    list_filter = (
        "event",
        "timestamp",
    )
    list_display = (
        "uuid",
        "timestamp",
        "user",
        "event",
        "obj",
        "extra",
    )
    search_fields = (
        "id",
        "object_id",
        "user__username",
        "user__email",
        "extra",
    )


class AccessTokenAdmin(Timestamped, VersionAdmin):
    list_display = ("uuid", "obj", "created_by", "expiry_time", "created")
    ordering = (
        "-created_time",
        "-modified_time",
        "-expiry_time",
    )
    search_fields = (
        "id",
        "obj",
        "created_by",
        "expiry_time",
    )


class SystemStatusAdmin(Timestamped, VersionAdmin):
    class Meta:
        verbose_name = "System Status"
        verbose_name_plural = "System Status"

    list_display = ("uuid", "message", "status", "modified_time", "priority", "active")
    ordering = ("-active", "-priority", "start_time", "-modified_time")


admin.site.register(MigrationRecorder.Migration, MigrationAdmin)

admin.site.register(User, LaxyUserAdmin)  # for our custom User model
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserObjectPermission, GuardianUserObjectPermissionAdmin)
admin.site.register(GroupObjectPermission, GuardianGroupObjectPermissionAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(ComputeResource, ComputeResourceAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(FileLocation, FileLocationAdmin)
admin.site.register(FileSet, FileSetAdmin)
admin.site.register(SampleCart, SampleCartAdmin)
admin.site.register(PipelineRun, PipelineRunAdmin)
admin.site.register(Pipeline, PipelineAdmin)
admin.site.register(EventLog, EventLogAdmin)
admin.site.register(AccessToken, AccessTokenAdmin)
admin.site.register(SystemStatus, SystemStatusAdmin)
