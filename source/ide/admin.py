from django.contrib import admin
from .models import Project, File, Directory


admin.site.register(Project)
admin.site.register(File)
admin.site.register(Directory)
