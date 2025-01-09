# views.py
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from .models import ChatRoom
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect


def get_or_create_private_room(user1, user2):
    """
    Get or create a private chat room between two users based on their usernames.
    """
    room_name = f"{min(user1.username, user2.username)}-{max(user1.username, user2.username)}"
    room, created = ChatRoom.objects.get_or_create(name=room_name)
    if created:
        room.participants.add(user1, user2)
    return room


def start_private_chat(request, user_id):
    """
    Start a private chat by redirecting to the room associated with the two users.
    """
    recipient = get_object_or_404(get_user_model(), id=user_id)
    room = get_or_create_private_room(request.user, recipient)
    return redirect('room', room_name=room.name)


class RoomView(TemplateView):
    template_name = 'chat.html'

    def get_context_data(self, **kwargs):
        """
        Get the context data for the chat room, including participants and messages.
        """
        context = super().get_context_data(**kwargs)
        room_name = self.kwargs['room_name']
        room = get_object_or_404(ChatRoom, name=room_name)
        current_user = self.request.user

        # Get the other participant(s) in the room (the user who isn't the current logged-in user)
        participants = room.participants.all()
        other_participants = [user for user in participants if user != current_user]

        # Assume there is only one recipient (in a 1-on-1 chat)
        if other_participants:
            recipient = other_participants[0]
        else:
            recipient = None  # Handle case if there is no other participant

        # Fetch all other chats the current user is part of (excluding the current chat room)
        other_chats = ChatRoom.objects.filter(participants=current_user).exclude(name=room_name)

        context.update({
            'room_name': room_name,
            'messages': room.messages.order_by('timestamp'),
            'recipient': recipient,
            'other_chats': other_chats,
        })

        return context

    def post(self, request, *args, **kwargs):
        """
        Handle actions such as deleting chat history.
        """
        action_map = {
            'delete_history': self.delete_history,
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)
        return HttpResponse("Invalid action", status=400)

    def delete_history(self, request):
        """
        Handle deleting chat history logic.
        """
        room_name = self.kwargs['room_name']
        room = get_object_or_404(ChatRoom, name=room_name)
        current_user = self.request.user

        # Ensure the current user is a participant in the room before allowing deletion
        if current_user not in room.participants.all():
            return HttpResponse("You are not authorized to delete chat history", status=403)

        # Delete all messages in the room
        room.messages.all().delete()

        return HttpResponseRedirect(self.request.path)
