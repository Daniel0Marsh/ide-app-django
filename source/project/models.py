from django.db import models
from django.conf import settings
from django.db.models import TextField
from django.db.models.signals import post_save
from django.dispatch import receiver
from user.models import ActivityLog


class Project(models.Model):
    """
    Represents a software project with theme, syntax settings, and user-related information.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Deleted', 'deleted'), ('Not Deleted', 'not_deleted')], default='not_deleted')
    project_name = models.CharField(max_length=100)
    project_path = models.CharField(max_length=100)
    repository = models.CharField(max_length=100, blank=True, null=True)
    project_description = TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    likes = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_projects', blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    collaborators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='collaborating_projects', blank=True)

    def __str__(self):
        return self.project_name

    def mark_as_deleted(self):
        # Set status to 'deleted'
        self.status = 'deleted'
        self.liked_by.clear()
        self.collaborators.clear()
        self.likes = 0
        self.save()


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


@receiver(post_save, sender=Task)
def create_task_notification(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.assigned_to,
            sender=instance.assigned_by,
            notification_type='task_created',
            message='',
            task=instance,
            project=instance.project
        )

    def __str__(self):
        return f"{self.title}"
