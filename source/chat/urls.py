# urls.py
from django.urls import path
from .views import RoomView, start_private_chat

urlpatterns = [
    path('chat/<str:room_name>/', RoomView.as_view(), name='room'),
    path('chat/direct/<int:user_id>/', start_private_chat, name='start_private_chat'),
]
