from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os
from enum import Enum


default_user_dir = os.path.join(settings.BASE_DIR, "UserDir")


class SenderEmailSettings(models.Model):
    sender_email = models.EmailField(
        max_length=255,
        verbose_name="Sender Email Address",
        help_text="The email address used as the sender for password reset and other emails."
    )

    def __str__(self):
        return self.sender_email


class DockerSessionStatus(Enum):
    """Enumeration for Docker session statuses."""
    RUNNING = 'running'
    STOPPED = 'stopped'
    REMOVED = 'removed'


class DockerSession(models.Model):
    """Model to represent a user's Docker session."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    container_id = models.CharField(max_length=255)
    container_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[(status.name, status.value) for status in DockerSessionStatus],
                              default=DockerSessionStatus.STOPPED.value)
    mounted_volume = models.CharField(max_length=255, null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)


class CustomUser(AbstractUser):
    """Custom user model extending the default user with additional fields."""
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    bio = models.TextField(blank=True)
    activity_log = models.JSONField(default=dict, blank=True)
    project_dir = models.CharField(max_length=512, null=True, blank=True)

    default_mem_limit = models.CharField(max_length=10, default='512m',
                                         help_text="Default memory limit for Docker containers.")
    default_memswap_limit = models.CharField(max_length=10, default='1g',
                                             help_text="Memory + swap limit for Docker containers.")
    default_cpus = models.DecimalField(max_digits=3, decimal_places=2, default=0.5,
                                       help_text="Number of CPUs allocated for Docker containers.")
    default_cpu_shares = models.PositiveIntegerField(default=512,
                                                     help_text="Relative CPU weight for Docker containers.")

    def __str__(self):
        """Return the username of the user."""
        return self.username

    def follow(self, user):
        """Follow another user."""
        self.following.add(user)

    def unfollow(self, user):
        """Unfollow another user."""
        self.following.remove(user)

    def is_following(self, user):
        """Check if the user is following another user."""
        return self.following.filter(id=user.id).exists()

    def is_followed_by(self, user):
        """Check if the user is followed by another user."""
        return self.followers.filter(id=user.id).exists()


class Notification(models.Model):
    """Represents a notification for a user."""
    NOTIFICATION_TYPES = [
        ('new_follower', 'New Follower'),
        ('new_task', 'New Task'),
        ('task_update', 'Task updated'),
        ('new_message', 'New Message'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                               related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    notification_enabled = models.BooleanField(default=True,
                                               help_text="Indicates whether this notification is enabled.")
    task = models.ForeignKey('project.Task', null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='notifications')
    project = models.ForeignKey('project.Project', null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='notifications')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def mark_as_read(self):
        """Mark the notification as read."""
        self.is_read = True
        self.save()

    def mark_as_unread(self):
        """Mark the notification as unread."""
        self.is_read = False
        self.save()

    def __str__(self):
        return f"Notification for {self.user.username}"


@receiver(post_save, sender=CustomUser)
def create_default_profile(sender, instance, created, **kwargs):
    """Automatically create default settings for a new user upon creation."""
    if created:
        # Set default profile picture if not provided
        if not instance.profile_picture:
            instance.profile_picture = 'profile_pictures/default.jpg'

        # Follow the admin user by default
        admin_user = CustomUser.objects.filter(is_superuser=True).first()
        if admin_user and admin_user != instance:
            instance.follow(admin_user)

        # Create a directory for the user's projects
        user_project_dir = os.path.join(default_user_dir, instance.username)
        if not os.path.exists(user_project_dir):
            os.makedirs(user_project_dir)

        instance.project_dir = user_project_dir
        instance.save()
