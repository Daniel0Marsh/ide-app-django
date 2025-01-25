from django.db import models
from django.conf import settings
from user.models import ActivityLog


class ChatRoom(models.Model):
    """Represents a chat room with participants."""
    name = models.CharField(max_length=255, unique=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='chat_rooms', blank=True
    )

    def __str__(self):
        return self.name


class Message(models.Model):
    """Represents a message sent within a chat room."""
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_messages', null=True, blank=True
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Override save to create a message notification for the recipient."""
        if self.recipient:
            ActivityLog.objects.create(
                user=self.recipient,
                sender=self.sender,
                activity_type='new_message',
                message='',
                task=None,
                project=None
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender} to {self.recipient}: {self.content[:20]}"
