import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from django.contrib.auth.models import User
        from django.contrib.auth import get_user_model
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user = self.scope["user"]

        # Get user profile image URL (or use a default if not set)
        profile_image_url = user.profile_picture.url if user.profile_picture else '/static/default-avatar.png'

        # Get the current timestamp
        timestamp = timezone.now().strftime('%b. %-d, %Y, %-I:%M %p')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': user.username,
                'profile_image_url': profile_image_url,
                'timestamp': timestamp,  # Add the timestamp
            }
        )

    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']
        profile_image_url = event['profile_image_url']
        timestamp = event['timestamp']  # Get the timestamp

        # Send message data to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
            'profile_image_url': profile_image_url,
            'timestamp': timestamp,  # Include timestamp
        }))


