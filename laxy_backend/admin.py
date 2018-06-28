from django.contrib import admin
import django.forms
from django.urls import reverse
from django.contrib.humanize.templatetags import humanize
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

from .models import URIValidator


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
                    '_location',
                    'created',
                    'modified')
    ordering = ('-created_time', '-modified_time',)
    form = FileAdminForm

    def _location(self, obj):
        url = reverse('laxy_backend:file_download',
                      kwargs={'uuid': obj.uuid(), 'filename': obj.name})
        return format_html('<a href="{}">{}</a>', url, obj.name)


class FileSetAdmin(Timestamped, VersionAdmin):
    list_display = ('uuid',
                    'created',
                    'modified')
    ordering = ('-created_time', '-modified_time',)


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
    search_fields = ('object_id',
                     'user__username',
                     'user__email',
                     'extra',)


# admin.site.register(TaskMeta, TaskMetaAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(ComputeResource, ComputeResourceAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(FileSet, FileSetAdmin)
admin.site.register(SampleSet, SampleSetAdmin)
admin.site.register(PipelineRun, PipelineRunAdmin)
admin.site.register(EventLog, EventLogAdmin)
