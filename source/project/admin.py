from django.contrib import admin
from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for the Project model."""
    fieldsets = (
        (None, {
            'fields': ('project_name', 'project_description', 'user', 'project_path', 'selected_theme', 'selected_syntax', 'is_public')
        }),
        ('Relationships', {
            'fields': ('likes', 'liked_by', 'collaborators')
        }),
    )
    list_display = ('project_name', 'user', 'is_public', 'likes')
    list_filter = ('is_public', 'created_at')
    search_fields = ('project_name', 'user__username', 'project_description')
    exclude = ('modified_at', 'created_at')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin configuration for the Task model."""
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'assigned_to', 'assigned_by', 'status', 'project')
        }),
    )
    list_display = ('title', 'assigned_to', 'assigned_by', 'status', 'project', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('title', 'assigned_to__username', 'assigned_by__username', 'project__project_name')
    exclude = ('created_at', 'updated_at')
