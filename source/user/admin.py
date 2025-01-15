from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, DockerSession


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('profile_picture', 'following', 'activity_log', 'project_dir'),
        }),
    )


@admin.register(DockerSession)
class DockerSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'container_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'container_id')