from datetime import datetime, timedelta

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.migrations.recorder import MigrationRecorder
import django.forms
from django.urls import reverse
from django.contrib.humanize.templatetags import humanize
from django.template.defaultfilters import truncatechars
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from reversion.admin import VersionAdmin

from django_object_actions import (DjangoObjectActions,
                                   takes_instance_or_queryset)

from laxy_backend.tasks import job as job_tasks
from .models import (Job,
                     ComputeResource,
                     File,
                     FileLocation,
                     FileSet,
                     SampleCart,
                     PipelineRun,
                     EventLog,
                     UserProfile,
                     AccessToken)

from .models import URIValidator

User = get_user_model()


def truncate_middle(text: str, middle='…', length=77, end=8) -> str:
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
        return text[:(length-8)] + middle + text[(-1*end):]
    else:
        return text


class Timestamped:
    list_display = ('uuid', 'created', 'modified',)
    ordering = ('-created_time', '-modified_time',)

    def uuid(self, obj):
        return '%s' % obj.uuid()

    def created(self, obj):
        return humanize.naturaltime(obj.created_time)

    def modified(self, obj):
        return humanize.naturaltime(obj.modified_time)


class MigrationAdmin(admin.ModelAdmin):
    ordering = ('-applied',)
    list_display = ('app', 'name', 'applied')
    readonly_fields = ('app', 'name', 'applied')


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class LaxyUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff',)
    list_select_related = ('profile',)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(LaxyUserAdmin, self).get_inline_instances(request, obj)


class UserProfileAdmin(admin.ModelAdmin):
    pass


class ComputeResourceAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid', 'name', 'address', 'priority', 'created', 'status_html')
    search_fields = ('id', 'name', 'host', 'status',)
    list_filter = ('status',)
    ordering = ('-priority', '-created_time',)

    color_mappings = {
        ComputeResource.STATUS_ONLINE: 'green',
        ComputeResource.STATUS_ERROR: 'red',
        ComputeResource.STATUS_STARTING: 'orange',
        ComputeResource.STATUS_TERMINATING: 'orange',
    }

    def status_html(self, obj):
        return format_html(
            '<span style="color: {};"><strong>{}</strong></span>',
            self.color_mappings.get(obj.status, 'black'),
            obj.get_status_display(),
        )

    def address(self, obj):
        if obj.status == ComputeResource.STATUS_ONLINE:
            return obj.host
        else:
            return ''


class JobAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid',
                    'created',
                    'modified',
                    'completed',
                    'expires',
                    '_compute_resource',
                    '_owner_email',
                    '_status')
    ordering = ('-created_time', '-completed_time', '-modified_time', '-expiry_time')
    search_fields = ('id', 'status', 'remote_id', 'owner_id__exact', 'owner__email__exact',)
    list_filter = ('status', 'expired',)
    actions = ('trigger_file_ingestion',
               'expire_job',
               'estimate_job_tarball_size',)

    color_mappings = {
        Job.STATUS_FAILED: 'red',
        Job.STATUS_CANCELLED: 'red',
        Job.STATUS_RUNNING: 'green',
    }

    def completed(self, obj: Job):
        return humanize.naturaltime(obj.completed_time)

    def expires(self, obj: Job):
        return humanize.naturaltime(obj.expiry_time)

    def _compute_resource(self, obj: Job):
        c = obj.compute_resource
        if c is not None:
            return format_html('%s (%s)' % (c.name, c.id))
        else:
            return ''

    def _status(self, obj: Job):
        return format_html(
            '<span style="color: {};"><strong>{}</strong></span>',
            self.color_mappings.get(obj.status, 'black'),
            obj.get_status_display(),
        )

    def _owner_email(self, obj: Job):
        if obj.owner:
            ct = ContentType.objects.get_for_model(obj.owner)
            user_url = reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=(obj.owner.id,))
            return format_html('<a href="{}">{} ({})</a>', user_url, obj.owner.email, obj.owner.id)
        return ''

    @takes_instance_or_queryset
    def trigger_file_ingestion(self, request, queryset):
        failed = []
        for obj in queryset:
            task_data = dict(job_id=obj.id)
            result = job_tasks.index_remote_files.apply_async(args=(task_data,))
            if result.failed():
                failed.append(obj.id)
        if not failed:
            self.message_user(request, "Ingesting !")
        else:
            self.message_user(request, "Errors trying to ingest %s" %
                              ','.join(failed))

    trigger_file_ingestion.short_description = "Ingest files"

    @takes_instance_or_queryset
    def estimate_job_tarball_size(self, request, queryset):
        failed = []
        for obj in queryset:
            task_data = dict(job_id=obj.id)
            result = job_tasks.estimate_job_tarball_size.apply_async(args=(task_data,))
            if result.failed():
                failed.append(obj.id)
        if not failed:
            self.message_user(request, "Starting task !")
        else:
            self.message_user(request, "Errors trying to estimate tarball size for %s" %
                              ','.join(failed))

    estimate_job_tarball_size.short_description = "Estimate tarball size (task)"

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
            self.message_user(request, "Errors trying to expire %s" %
                              ','.join(failed))

    expire_job.short_description = "Expire job (delete large files)"


def do_nothing_validator(value):
    return None


class FileLocationAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'file',
                    'default',
                    '_url',)
    # raw_id_fields = ('file',)
    readonly_fields = ('url', 'file',)

    ordering = ('-default',)
    search_fields = ('url', 'file__id',)

    def _url(self, obj):
        return format_html('<a href="{}">{}</a>',
                           obj.url,
                           truncate_middle(obj.url, end=32))


class FileLocationAdminForm(django.forms.ModelForm):
    class Meta:
        model = FileLocation
        fields = '__all__'

    url = django.forms.CharField(max_length=2048, validators=[URIValidator()])


class FileLocationsInline(admin.TabularInline):
    model = FileLocation
    readonly_fields = ('id', 'default', 'url',)
    fields = ('id', 'default', 'url',)
    ordering = ('-default',)
    can_delete = False
    verbose_name_plural = 'File Locations'
    fk_name = 'file'
    extra = 0


class FileAdminForm(django.forms.ModelForm):
    class Meta:
        model = File
        fields = '__all__'

    location = django.forms.CharField(max_length=2048, validators=[URIValidator()])


class FileAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid',
                    '_path',
                    '_name',
                    'location',
                    'created',
                    'modified')
    readonly_fields = ('location',)
    ordering = ('-created_time', '-modified_time',)
    search_fields = ('id', 'path', 'name',)
    inlines = (FileLocationsInline, )
    actions = ('fix_metadata',)
    form = FileAdminForm

    truncate_to = 32

    def _path(self, obj):
        return truncatechars(obj.path, self.truncate_to)

    def _name(self, obj):
        return truncatechars(obj.name, self.truncate_to)

    def location(self, obj):
        url = reverse('laxy_backend:file_download',
                      kwargs={'uuid': obj.uuid(), 'filename': obj.name})
        return format_html('<a href="{}">{}</a>',
                           url,
                           truncatechars(obj.name, self.truncate_to))

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
        last_msg = ''
        for obj in queryset:
            if isinstance(obj.metadata, str):
                obj.metadata = dict()
                obj.save()
                count += 1
                last = f" (last was for File {obj.id})"
        self.message_user(request, f"Fix {count} metadata fields{last_msg}")

    fix_metadata.short_description = "Fix invalid file metadata"


class JobInputFilesInline(admin.TabularInline):
    model = Job
    readonly_fields = ('id', 'status', 'owner', 'completed_time',)
    fields = ('id', 'status', 'owner', 'completed_time',)
    can_delete = False
    verbose_name_plural = 'Associated Job (as input FileSet)'
    fk_name = 'input_files'
    extra = 0


class JobOutputFilesInline(admin.TabularInline):
    model = Job
    readonly_fields = ('id', 'status', 'owner', 'completed_time',)
    fields = ('id', 'status', 'owner', 'completed_time',)
    can_delete = False
    verbose_name_plural = 'Associated Job (as output FileSet)'
    fk_name = 'output_files'
    extra = 0


class FilesInline(admin.TabularInline):
    model = File
    readonly_fields = ('id',)
    fields = ('id', 'path', 'name', 'type_tags',)
    ordering = ('path', 'name',)
    can_delete = False
    verbose_name_plural = 'Files'
    fk_name = 'fileset'
    extra = 0


class FileSetAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid',
                    'path',
                    'name',
                    'created',
                    'modified')
    ordering = ('-created_time', '-modified_time',)
    search_fields = ('id', 'name', 'path',)
    inlines = (JobInputFilesInline, JobOutputFilesInline, FilesInline,)


class SampleCartAdmin(Timestamped, VersionAdmin):
    pass


class PipelineRunAdmin(Timestamped, VersionAdmin):
    pass


class EventLogAdmin(admin.ModelAdmin):
    ordering = ('-timestamp',)
    raw_id_fields = ('user',)
    list_filter = ('event',
                   'timestamp',)
    list_display = ('uuid',
                    'timestamp',
                    'user',
                    'event',
                    'obj',
                    'extra',)
    search_fields = ('id',
                     'object_id',
                     'user__username',
                     'user__email',
                     'extra',)


class AccessTokenAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid',
                    'obj',
                    'created_by',
                    'expiry_time',
                    'created')
    ordering = ('-created_time', '-modified_time', '-expiry_time',)
    search_fields = ('id', 'obj', 'created_by', 'expiry_time',)


admin.site.register(MigrationRecorder.Migration, MigrationAdmin)

admin.site.register(User, LaxyUserAdmin)  # for our custom User model
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(ComputeResource, ComputeResourceAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(FileLocation, FileLocationAdmin)
admin.site.register(FileSet, FileSetAdmin)
admin.site.register(SampleCart, SampleCartAdmin)
admin.site.register(PipelineRun, PipelineRunAdmin)
admin.site.register(EventLog, EventLogAdmin)
admin.site.register(AccessToken, AccessTokenAdmin)
