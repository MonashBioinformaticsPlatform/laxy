from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
import django.forms
from django.urls import reverse
from django.contrib.humanize.templatetags import humanize
from django.template.defaultfilters import truncatechars
from django.utils.html import format_html
from reversion.admin import VersionAdmin

from django_object_actions import (DjangoObjectActions,
                                   takes_instance_or_queryset)

from laxy_backend import tasks
from .models import (Job,
                     ComputeResource,
                     File,
                     FileSet,
                     SampleSet,
                     PipelineRun,
                     EventLog)

from .models import URIValidator, User


class Timestamped:
    list_display = ('uuid', 'created', 'modified',)
    ordering = ('-created_time', '-modified_time',)

    def uuid(self, obj):
        return '%s' % obj.uuid()

    def created(self, obj):
        return humanize.naturaltime(obj.created_time)

    def modified(self, obj):
        return humanize.naturaltime(obj.modified_time)


class ComputeResourceAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid', 'name', 'address', 'created', 'status_html')
    search_fields = ('id', 'name', 'host', 'status',)
    list_filter = ('status',)
    ordering = ('-created_time',)

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
                    '_compute_resource',
                    '_status')
    ordering = ('-created_time', '-completed_time', '-modified_time',)
    search_fields = ('id', 'status', 'compute_resource', 'remote_id',)
    list_filter = ('status',)
    actions = ('trigger_file_ingestion',)

    color_mappings = {
        Job.STATUS_FAILED: 'red',
        Job.STATUS_CANCELLED: 'red',
        Job.STATUS_RUNNING: 'green',
    }

    def completed(self, obj):
        return humanize.naturaltime(obj.completed_time)

    def _compute_resource(self, obj):
        c = obj.compute_resource
        if c is not None:
            return format_html('%s (%s)' % (c.id, c.host))
        else:
            return ''

    def _status(self, obj):
        return format_html(
            '<span style="color: {};"><strong>{}</strong></span>',
            self.color_mappings.get(obj.status, 'black'),
            obj.get_status_display(),
        )

    @takes_instance_or_queryset
    def trigger_file_ingestion(self, request, queryset):
        failed = []
        for obj in queryset:
            task_data = dict(job_id=obj.id)
            result = tasks.index_remote_files.apply_async(args=(task_data,))
            if result.failed():
                failed.append(obj.id)
        if not failed:
            self.message_user(request, "Ingesting !")
        else:
            self.message_user(request, "Errors trying to ingest %s" %
                              ','.join(failed))

    trigger_file_ingestion.short_description = "Ingest files"


def do_nothing_validator(value):
    return None


class FileAdminForm(django.forms.ModelForm):
    class Meta:
        model = File
        fields = '__all__'

    location = django.forms.CharField(max_length=2048, validators=[URIValidator()])


class FileAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid',
                    '_path',
                    '_name',
                    '_location',
                    'created',
                    'modified')
    ordering = ('-created_time', '-modified_time',)
    search_fields = ('id', 'path', 'name',)
    form = FileAdminForm

    truncate_to = 32

    def _path(self, obj):
        return truncatechars(obj.path, self.truncate_to)

    def _name(self, obj):
        return truncatechars(obj.name, self.truncate_to)

    def _location(self, obj):
        url = reverse('laxy_backend:file_download',
                      kwargs={'uuid': obj.uuid(), 'filename': obj.name})
        return format_html('<a href="{}">{}</a>',
                           url,
                           truncatechars(obj.name, self.truncate_to))


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
    fields = ('id', 'path', 'name',)
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


class SampleSetAdmin(Timestamped, VersionAdmin):
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


admin.site.register(User, UserAdmin)  # for our custom User model
admin.site.register(Job, JobAdmin)
admin.site.register(ComputeResource, ComputeResourceAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(FileSet, FileSetAdmin)
admin.site.register(SampleSet, SampleSetAdmin)
admin.site.register(PipelineRun, PipelineRunAdmin)
admin.site.register(EventLog, EventLogAdmin)
