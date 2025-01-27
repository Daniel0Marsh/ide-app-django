from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/(?P<username>\w+)/(?P<project_name>[\w\-]+)/editor/$', consumers.TerminalConsumer.as_asgi()),
]
