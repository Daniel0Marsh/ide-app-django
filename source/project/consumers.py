import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async


class TerminalConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling terminal commands within a project context.
    """

    async def connect(self):
        """
        Establish connection, retrieve user and project, and join room group.
        """
        self.username = self.scope['url_route']['kwargs']['username']
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        self.user = await self.get_user(self.username)
        if not self.user:
            await self.close()

        self.project = await self.get_project(self.project_id)
        if not self.project:
            await self.close()

        self.room_group_name = f"terminal_{self.user.id}_{self.project.id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """
        Remove channel from room group on disconnect.
        """
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Handle received message and send terminal command output or error.
        """
        text_data_json = json.loads(text_data)
        command = text_data_json.get('command', None)

        if command:
            response = await self.execute_terminal_command(command)
            await self.send(text_data=json.dumps(response))

    async def execute_terminal_command(self, command):
        """
        Execute terminal command and return result or error.
        """
        from .utils import ProjectContainerManager
        container_manager = ProjectContainerManager(project=self.project, user=self.user)

        try:
            result = await sync_to_async(container_manager.execute_command)(command)
            return {
                'type': 'terminal_output',
                'output': result['formatted_output'],
                'exit_code': result['exit_code']
            }
        except Exception as e:
            return {
                'type': 'terminal_error',
                'error': str(e)
            }

    @sync_to_async
    def get_user(self, username):
        """
        Retrieve user by username.
        """
        from django.contrib.auth import get_user_model
        try:
            return get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            return None

    @sync_to_async
    def get_project(self, project_id):
        """
        Retrieve project by ID.
        """
        from .models import Project
        try:
            return Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return None
