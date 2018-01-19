from django.contrib import admin
from reversion.admin import VersionAdmin

from .models import Job, ComputeResource, File, FileSet


class ComputeResourceAdmin(VersionAdmin):
    pass


class JobAdmin(VersionAdmin):
    pass


class FileAdmin(VersionAdmin):
    pass


class FileSetAdmin(VersionAdmin):
    pass


# admin.site.register(TaskMeta, TaskMetaAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(ComputeResource, ComputeResourceAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(FileSet, FileSetAdmin)
