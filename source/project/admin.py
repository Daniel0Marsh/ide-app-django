from django.contrib import admin
from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Admin interface for managing projects.
    """
    list_display = ('project_name', 'user', 'is_public', 'likes', 'modified_at', 'created_at')
    list_filter = ('is_public', 'selected_theme', 'selected_syntax', 'created_at', 'modified_at')
    search_fields = ('project_name', 'user__username', 'repository', 'project_description')
    ordering = ('-created_at',)
    filter_horizontal = ('collaborators', 'liked_by')
    readonly_fields = ('modified_at', 'created_at', 'likes')

    fieldsets = (
        (None, {
            'fields': ('user', 'project_name', 'project_path', 'repository', 'project_description')
        }),
        ('Appearance', {
            'fields': ('selected_theme', 'selected_syntax')
        }),
        ('Privacy & Collaboration', {
            'fields': ('is_public', 'collaborators')
        }),
        ('Likes & Statistics', {
            'fields': ('likes', 'liked_by', 'modified_at', 'created_at')
        }),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Admin interface for managing tasks.
    """
    list_display = ('title', 'project', 'assigned_to', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('title', 'project__project_name', 'assigned_to__username', 'assigned_by__username')
    ordering = ('-created_at',)
    autocomplete_fields = ('project', 'assigned_to', 'assigned_by')

    fieldsets = (
        (None, {
            'fields': ('project', 'title', 'description', 'status')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'assigned_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
