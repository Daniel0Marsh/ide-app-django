from django.db import models
import os
from django.db.models import TextField
from django.conf import settings


default_project_path = file_path = os.path.join(settings.BASE_DIR, "UserProjects")
default_project_help = """ 
Requirements/n
Django
CodeMirror API
Bootstrap API
Installation
Clone this repository.
Install the required dependencies using pip:
pip install -r requirements.txt
Usage
Ensure your Django project is set up.
Add 'ide' to the INSTALLED_APPS list in your Django project settings.
Include the URLs from the IDE app in your project's urls.py.
Run migrations to create necessary database tables:
python manage.py makemigrations
python manage.py migrate
Build the Docker Image:
sudo docker build -t terminal_session .
You can remove the docker image as follows:
docker rmi -f terminal_session
Add User to Docker Group and set permissions:
sudo usermod -aG docker your_username
sudo chmod 666 /var/run/docker.sock
Start your Django development server:
python manage.py runserver
Navigate to the IDE app's URL in your browser to access the IDE. http:127.0.0.1:8000
Functionality
Project Management: Create, edit, rename, and organize files and folders within the project tree.
Download Project: Download the entire project for offline access or sharing with others.
Auto Syntax Highlighting: Automatically highlight syntax for various programming languages for improved readability.
Multiple Themes: Choose from a variety of themes to personalize your coding environment.
"""
default_project_git = """
Some text to explain how to use git...
"""


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
    project_path = models.CharField(max_length=100, default=default_project_path)
    project_description = TextField(blank=True, null=True)
    selected_theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='default')
    selected_syntax = models.CharField(max_length=20, choices=SYNTAX_CHOICES, default='auto')
    modified_at = models.DateTimeField(auto_now=True)
    help = TextField(default=default_project_help)
    git = TextField(default=default_project_git)


    def __str__(self):
        return self.project_name
