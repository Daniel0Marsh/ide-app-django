from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import path
from .models import CustomUser, DockerSession, ActivityLog, IDESettings, Subscription
from django.contrib.auth.admin import UserAdmin


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_name', 'mem_limit', 'memswap_limit', 'cpus', 'storage_limit', 'created_at', 'expires_at')
    list_filter = ('plan_name', 'created_at')
    search_fields = ('user__username', 'stripe_customer_id', 'stripe_subscription_id')
    readonly_fields = ('stripe_customer_id', 'stripe_subscription_id', 'created_at')


admin.site.register(Subscription, SubscriptionAdmin)


class IDESettingsInline(admin.StackedInline):
    """
    Inline admin interface for IDESettings.
    """
    model = IDESettings
    can_delete = False
    readonly_fields = (
        'selected_theme',
        'selected_syntax',
        'show_line_numbers',
        'auto_close_brackets',
        'match_brackets',
        'highlight_current_line',
        'line_wrapping',
        'indent_with_tabs',
        'linting',
        'tab_size',
        'font_size'
    )
    verbose_name = "IDE Settings"


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
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Project Info', {'fields': ('project_dir',)}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')
        }),
    )

    inlines = [IDESettingsInline]


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
