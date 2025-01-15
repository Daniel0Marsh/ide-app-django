import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json.get("action")

        if action == "join":
            await self.handle_join(text_data_json)
        elif action == "message":
            await self.handle_message(text_data_json)

    async def handle_join(self, text_data_json):
        recipient_id = text_data_json.get("recipient_id")
        room_name = text_data_json.get("roomName")  # The roomName is now directly provided

        if not recipient_id:
            await self.send_error("recipient_id is missing in the join action.")
            return

        if not room_name:
            await self.send_error("room_name is missing in the join action.")
            return

        self.room_group_name = room_name  # Using the provided room_name directly
        await self.get_or_create_chat_room(self.room_group_name)

        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )

    async def handle_message(self, text_data_json):
        if not self.room_group_name:
            await self.send_error("room_group_name is not set. Did you join a room first?")
            return

        message = text_data_json.get("message")
        recipient_id = text_data_json.get("recipient_id")
        user = self.scope["user"]

        room = await self.get_chat_room(self.room_group_name)
        await self.save_message(room, user, recipient_id, message)

        profile_image_url = (
            user.profile_picture.url if user.profile_picture else "/static/default-avatar.png"
        )
        timestamp = timezone.now().strftime("%b. %-d, %Y, %-I:%M %p")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender": user.username,
                "profile_image_url": profile_image_url,
                "timestamp": timestamp,
                "recipient_id": recipient_id,
                "roomName": self.room_group_name,
            },
        )

    async def send_error(self, error_message):
        await self.send(text_data=json.dumps({"error": error_message}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def get_chat_room(self, room_name):
        from .models import ChatRoom
        return ChatRoom.objects.get(name=room_name)

    @sync_to_async
    def get_or_create_chat_room(self, room_name):
        from .models import ChatRoom
        from django.contrib.auth import get_user_model

        User = get_user_model()

        room, created = ChatRoom.objects.get_or_create(name=room_name)
        if created:
            participant_ids = [int(id_str) for id_str in room_name.split("-") if id_str.isdigit()]
            participants = User.objects.filter(id__in=participant_ids)

            if len(participants) != 2:
                raise ValueError("Room name must correspond to exactly two valid users.")

            room.participants.add(*participants)
        return room

    @sync_to_async
    def save_message(self, room, sender, recipient_id, message):
        from .models import Message
        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return

        Message.objects.create(
            room=room, sender=sender, recipient=recipient, content=message, timestamp=timezone.now()
        )
