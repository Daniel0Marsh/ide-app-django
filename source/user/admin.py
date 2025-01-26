from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import path
from .models import SenderEmailSettings, CustomUser, DockerSession, ActivityLog
from django.contrib.auth.admin import UserAdmin


@admin.register(SenderEmailSettings)
class SenderEmailSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for managing SenderEmailSettings.
    Ensures only one instance can exist.
    """
    list_display = ('sender_email',)
    search_fields = ('sender_email',)

    def has_add_permission(self, request):
        """Prevent adding new SenderEmailSettings if one already exists."""
        if SenderEmailSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the SenderEmailSettings instance."""
        return False

    def changelist_view(self, request, extra_context=None):
        """
        Redirect to the change form if the instance exists.
        """
        if SenderEmailSettings.objects.exists():
            obj = SenderEmailSettings.objects.first()
            return HttpResponseRedirect(f"/admin/app_name/senderemailsettings/{obj.id}/change/")
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin interface for CustomUser.
    """
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'date_joined', 'project_dir')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'bio', 'profile_picture')}),
        ('Docker Settings', {
            'fields': (
                'default_mem_limit', 'default_memswap_limit',
                'default_cpus', 'default_cpu_shares'
            )
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Project Info', {'fields': ('project_dir',)}),  # Added project_dir
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')
        }),
    )



@admin.register(DockerSession)
class DockerSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for DockerSession.
    """
    list_display = ('user', 'container_name', 'status', 'created_at', 'last_activity_at')
    search_fields = ('user__username', 'container_name')
    list_filter = ('status', 'created_at')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """
    Admin interface for ActivityLog.
    """
    list_display = ('user', 'activity_type', 'created_at', 'notification_enabled')
    search_fields = ('user__username', 'activity_type', 'message')
    list_filter = ('activity_type', 'created_at', 'notification_enabled')
    raw_id_fields = ('user', 'sender', 'task', 'project')
