from typing import Union, Sequence

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
    UserProfile,
    AccessToken,
    URIValidator,
)

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
        "modified",
        "completed",
        "expires",
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
            task_data = dict(job_id=obj.id, clobber=True)
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
            obj.expiry_time = datetime.now() - timedelta(seconds=5)
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
        "owner",
    )
    list_display = (
        "name",
        "uuid",
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
