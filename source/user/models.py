from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os

default_user_dir = os.path.join(settings.BASE_DIR, "UserDir")


class DockerSession(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    container_id = models.CharField(max_length=255)
    container_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20,
                              choices=[('running', 'Running'), ('stopped', 'Stopped'), ('removed', 'Removed')],
                              default='stopped')
    mounted_volume = models.CharField(max_length=255, null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)


from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    following = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='followers',
        blank=True
    )
    bio = models.TextField(null=True, blank=True)
    activity_log = models.JSONField(default=dict, blank=True)
    project_dir = models.CharField(max_length=512, null=True, blank=True)

    # Default Docker resource allocation settings
    default_mem_limit = models.CharField(
        max_length=10,
        default='512m',
        help_text="Default memory limit for the user's Docker containers (e.g., '512m' for 512MB)."
    )
    default_memswap_limit = models.CharField(
        max_length=10,
        default='1g',
        help_text="Default memory + swap limit for the user's Docker containers (e.g., '1g' for 1GB)."
    )
    default_cpus = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.5,
        help_text="Default number of CPUs allocated for the user's Docker containers (e.g., 0.5 for half a CPU)."
    )
    default_cpu_shares = models.PositiveIntegerField(
        default=512,
        help_text="Default relative CPU weight for the user's Docker containers (higher value = higher priority)."
    )

    def __str__(self):
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



# Signal to create a default profile and user project directory
@receiver(post_save, sender=CustomUser)
def create_default_profile(sender, instance, created, **kwargs):
    if created:
        # Set a default profile picture if not provided
        if not instance.profile_picture:
            instance.profile_picture = 'profile_pictures/default.jpg'
            instance.save()

        # Optionally, automatically follow an admin user
        admin_user = CustomUser.objects.filter(is_superuser=True).first()
        if admin_user and admin_user != instance:
            instance.follow(admin_user)

        # Create user-specific directory for projects
        user_project_dir = os.path.join(default_user_dir, instance.username)
        if not os.path.exists(user_project_dir):
            os.makedirs(user_project_dir)

        # Store the path of the project directory in the user's model
        instance.project_dir = user_project_dir
        instance.save()
