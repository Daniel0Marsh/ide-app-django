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
    selected_theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='default')
    selected_syntax = models.CharField(max_length=20, choices=SYNTAX_CHOICES, default='auto')


class File(models.Model):
    """
    Model representing a file within a project.

    Attributes:
        project (Project): The project to which the file belongs.
        file_name (str): The name of the file.
        contents (str): The contents of the file.
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file_name = models.CharField(max_length=255)
    contents = models.TextField(blank=True, null=True)


class Directory(models.Model):
    """
    Model representing a directory within a project.

    Attributes:
        project (Project): The project to which the directory belongs.
        directory_name (str): The name of the directory.
        files (QuerySet): A queryset of files contained within the directory.
        parent_directory (Directory): The parent directory of the current directory.
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='directories')
    directory_name = models.CharField(max_length=255)
    files = models.ManyToManyField('File')
    parent_directory = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subdirectories')
