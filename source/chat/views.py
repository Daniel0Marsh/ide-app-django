# views.py
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from .models import ChatRoom, Message
from django.shortcuts import redirect
from django.contrib.auth import get_user_model


def get_or_create_private_room(user1, user2):
    # Use usernames instead of IDs for room naming
    room_name = f"{min(user1.username, user2.username)}-{max(user1.username, user2.username)}"
    room, created = ChatRoom.objects.get_or_create(name=room_name)
    if created:
        room.participants.add(user1, user2)
    return room


def start_private_chat(request, user_id):
    recipient = get_object_or_404(get_user_model(), id=user_id)
    room = get_or_create_private_room(request.user, recipient)
    return redirect('room', room_name=room.name)


class RoomView(TemplateView):
    template_name = 'chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room_name = self.kwargs['room_name']
        room = get_object_or_404(ChatRoom, name=room_name)
        context['room_name'] = room_name
        context['messages'] = room.messages.order_by('timestamp')

        # Get the current logged-in user
        current_user = self.request.user

        # Get the other participant(s) in the room (the user who isn't the current logged-in user)
        participants = room.participants.all()
        other_participants = [user for user in participants if user != current_user]

        # Assume there is only one recipient (in a 1-on-1 chat)
        if other_participants:
            context['recipient'] = other_participants[0]
        else:
            context['recipient'] = None  # Handle case if there is no other participant

        return context
