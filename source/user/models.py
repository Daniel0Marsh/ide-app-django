from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os
from enum import Enum

default_user_dir = os.path.join(settings.BASE_DIR, "UserDir")


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
    bio = models.TextField(null=True, blank=True)
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
