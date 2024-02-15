from django.db import models


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

    project_name = models.CharField(max_length=100)
    project_path = models.CharField(max_length=100, default="/home/user/dev/codeblock_projects/django-ide-app/source/projects")
    selected_theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='default')
    selected_syntax = models.CharField(max_length=20, choices=SYNTAX_CHOICES, default='auto')

    def __str__(self):
        return self.project_name