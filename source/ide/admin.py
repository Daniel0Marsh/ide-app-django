from django.contrib import admin
from .models import Project, File, Directory


class DirectoryInline(admin.StackedInline):
    model = Directory
    extra = 0


class FileInline(admin.TabularInline):
    model = File
    extra = 0


class ProjectAdmin(admin.ModelAdmin):
    inlines = [DirectoryInline, FileInline]


admin.site.register(Project, ProjectAdmin)
