from django.db import models
from django.conf import settings


class ChatRoom(models.Model):
    """Model to represent a chat room."""
    name = models.CharField(max_length=255, unique=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='chat_rooms', blank=True
    )

    def __str__(self):
        return self.name


class Message(models.Model):
    """Model to store messages."""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} to {self.recipient}: {self.content[:20]}"
