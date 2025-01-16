from django.contrib import admin
from .models import ChatRoom, Message
from user.models import Notification


# Inline admin for Message model
class MessageInline(admin.TabularInline):
    """Inline admin for the Message model within a ChatRoom."""
    model = Message
    extra = 0
    readonly_fields = ('sender', 'recipient', 'timestamp')


# Admin class for the ChatRoom model
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin interface for the ChatRoom model with inline Message management."""
    list_display = ('name', 'get_participants_count')
    search_fields = ('name',)
    inlines = [MessageInline]
    ordering = ('name',)

    def get_participants_count(self, obj):
        """Custom method to display the number of participants in a chat room."""
        return obj.participants.count()
    get_participants_count.short_description = 'Participants Count'


# Admin class for the Message model
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for the Message model."""
    list_display = ('sender', 'recipient', 'room', 'timestamp', 'content_preview')
    search_fields = ('sender__username', 'recipient__username', 'content')
    ordering = ('-timestamp',)
    list_filter = ('room', 'sender', 'recipient')

    def content_preview(self, obj):
        """Show a preview of the message content."""
        return obj.content[:20] + '...' if len(obj.content) > 20 else obj.content
    content_preview.short_description = 'Content Preview'


# Register models and their admin classes
admin.site.register(ChatRoom, ChatRoomAdmin)
admin.site.register(Message, MessageAdmin)
