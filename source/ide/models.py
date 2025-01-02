from django.db import models
from django.db.models import TextField
from django.conf import settings
import os

default_project_path = file_path = os.path.join(settings.BASE_DIR, "UserProjects")


class Project(models.Model):
    """
    Model representing a software project with configured theme and syntax settings.

    Attributes:
        project_name (str): The name of the project.
        selected_theme (str): The selected theme for the project.
        selected_syntax (str): The selected syntax highlighting for the project.
    """

    # Define choices for themes
    THEME_CHOICES = [
        ('default', 'Light Mode'),
        ('eclipse', 'Eclipse'),
        ('material', 'Material'),
        ('cobalt', 'Cobalt'),
        ('monokai', 'Monokai'),
        ('dracula', 'Dracula'),
    ]

    # Define choices for syntax
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
    project_path = models.CharField(max_length=100, default=default_project_path)
    project_description = TextField(blank=True, null=True)
    selected_theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='default')
    selected_syntax = models.CharField(max_length=20, choices=SYNTAX_CHOICES, default='auto')
    modified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    collaborators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='collaborating_projects', blank=True)

    def __str__(self):
        return self.project_name
