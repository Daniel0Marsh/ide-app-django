from django.db import models
from django.conf import settings
from django.db.models import TextField


class Project(models.Model):
    """
    Represents a software project with theme, syntax settings, and user-related information.
    """
    THEME_CHOICES = [
        ('default', 'Light Mode'),
        ('eclipse', 'Eclipse'),
        ('material', 'Material'),
        ('cobalt', 'Cobalt'),
        ('monokai', 'Monokai'),
        ('dracula', 'Dracula'),
    ]

    SYNTAX_CHOICES = [
        ('auto', 'Auto Detect'),
        ('plain', 'Plain Text'),
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('html', 'HTML'),
        ('css', 'CSS'),
        ('java', 'Java'),
        ('c', 'C'),
        ('cpp', 'C++'),
        ('php', 'PHP'),
        ('ruby', 'Ruby'),
        ('swift', 'Swift'),
        ('go', 'Go'),
        ('rust', 'Rust'),
        ('typescript', 'TypeScript'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=100)
    project_path = models.CharField(max_length=100)
    project_description = TextField(blank=True, null=True)
    selected_theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='default')
    selected_syntax = models.CharField(max_length=20, choices=SYNTAX_CHOICES, default='auto')
    is_public = models.BooleanField(default=False)
    likes = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_projects', blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    collaborators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='collaborating_projects', blank=True)

    def __str__(self):
        return self.project_name


class Task(models.Model):
    """
    Represents a task assigned to a user for a project.
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks_assigned_by')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"
