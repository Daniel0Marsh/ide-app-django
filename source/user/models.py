from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import os
from enum import Enum


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('full', 'Full'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255, unique=True)
    stripe_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    plan_name = models.CharField(max_length=50, choices=PLAN_CHOICES, default='free')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    mem_limit = models.CharField(max_length=10, default='512m',
                                         help_text="Memory limit for Docker containers.")
    memswap_limit = models.CharField(max_length=10, default='1g',
                                             help_text="Memory + swap limit for Docker containers.")
    cpus = models.DecimalField(max_digits=3, decimal_places=2, default=0.5,
                                       help_text="Number of CPUs allocated for Docker containers.")
    cpu_shares = models.PositiveIntegerField(default=512,
                                                     help_text="Relative CPU weight for Docker containers.")
    storage_limit = models.PositiveIntegerField(default=10000,
                                                     help_text="Maximum size of the directory containing all user projects in megabytes (MB).")

    def __str__(self):
        return f"{self.user.username} - {self.get_plan_name_display()}"

    def save(self, *args, **kwargs):
        # Set plan-specific values
        if self.plan_name == 'free':
            self.mem_limit = '512m'
            self.memswap_limit = '1g'
            self.cpus = 0.5
            self.cpu_shares = 512
            self.storage_limit = 10000  # 10GB for free users

        elif self.plan_name == 'basic':
            self.mem_limit = '1g'
            self.memswap_limit = '2g'
            self.cpus = 1.0
            self.cpu_shares = 1024
            self.storage_limit = 50000  # 50GB for basic users

        elif self.plan_name == 'full':
            self.mem_limit = '4g'
            self.memswap_limit = '8g'
            self.cpus = 4.0
            self.cpu_shares = 2048
            self.storage_limit = 200000  # 200GB for full users

        super().save(*args, **kwargs)


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
    is_active = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    bio = models.TextField(blank=True)
    project_dir = models.CharField(max_length=512, null=True, blank=True)

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


class ActivityLog(models.Model):
    """Represents an activity entry for a user."""
    NOTIFICATION_TYPES = [
        ('new_follower', 'New Follower'),
        ('new_message', 'New Message'),
        ('task_created', 'Task Created'),
        ('task_updated', 'Task Updated'),
        ('task_deleted', 'Task deleted'),
        ('project_created', 'Project Created'),
        ('project_updated', 'Project Updated'),
        ('project_deleted', 'Project Deleted'),
        ('collaborator_added', 'Collaborator Added')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                               related_name='sent_activity')
    activity_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    notification_enabled = models.BooleanField(default=True,
                                               help_text="Indicates whether this notification is enabled.")
    task = models.ForeignKey('project.Task', null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='activity')
    project = models.ForeignKey('project.Project', null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='activity')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        super(ActivityLog, self).save(*args, **kwargs)

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
        user_project_dir = os.path.join(os.path.join(settings.BASE_DIR, "UserDir"), instance.username)
        if not os.path.exists(user_project_dir):
            os.makedirs(user_project_dir)

        instance.project_dir = user_project_dir
        instance.save()

        # Create default IDE settings for the user
        IDESettings.objects.create(user=instance)

        # Create a default subscription for the user (e.g., 'free' plan)
        Subscription.objects.create(
            user=instance,
            stripe_customer_id=None,
            plan_name='free',
        )


class IDESettings(models.Model):
    """
    Represents the IDE settings for a user, ensuring one instance per user.
    """
    THEME_CHOICES = [
        ('dracula', 'Dracula'),
        ('monokai', 'Monokai'),
        ('ayu-dark', 'Ayu Dark'),
        ('light-mode', 'Light Mode'),
        ('eclipse', 'Eclipse'),
        ('solarized-light', 'Solarized Light'),
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

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    selected_theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='dracula')
    selected_syntax = models.CharField(max_length=20, choices=SYNTAX_CHOICES, default='auto')
    show_line_numbers = models.BooleanField(default=True)
    auto_close_brackets = models.BooleanField(default=True)
    match_brackets = models.BooleanField(default=True)
    highlight_current_line = models.BooleanField(default=True)
    line_wrapping = models.BooleanField(default=True)
    indent_with_tabs = models.BooleanField(default=True)
    linting = models.BooleanField(default=True)
    tab_size = models.IntegerField(default=4)
    font_size = models.IntegerField(default=14)

    def __str__(self):
        return f"{self.user.username}'s IDE Settings"
