from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, DockerSession


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for the CustomUser model, adding custom fields to the user interface."""
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': (
                'profile_picture', 'following', 'activity_log', 'project_dir',
                'default_mem_limit', 'default_memswap_limit', 'default_cpus', 'default_cpu_shares'
            ),
        }),
    )
    list_display = UserAdmin.list_display + ('default_mem_limit', 'default_cpus', 'project_dir')


@admin.register(DockerSession)
class DockerSessionAdmin(admin.ModelAdmin):
    """Admin configuration for the DockerSession model."""
    list_display = ('user', 'container_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'container_id')
