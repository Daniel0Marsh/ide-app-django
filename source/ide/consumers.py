import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async


class TerminalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        self.user = await self.get_user(self.username)
        if not self.user:
            await self.close()  # Close if user not found

        self.project = await self.get_project(self.project_id)
        if not self.project:
            await self.close()  # Close if project not found

        self.room_group_name = f"terminal_{self.user.id}_{self.project.id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        command = text_data_json.get('command', None)

        if command:
            response = await self.execute_terminal_command(command)
            await self.send(text_data=json.dumps(response))

    async def execute_terminal_command(self, command):
        from .utils import ProjectContainerManager
        container_manager = ProjectContainerManager(project=self.project, user=self.user)

        try:
            # Ensure this call is wrapped with sync_to_async
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
        from django.contrib.auth import get_user_model
        try:
            return get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            return None

    @sync_to_async
    def get_project(self, project_id):
        # Importing the Project model locally to avoid AppRegistryNotReady error
        from .models import Project
        try:
            return Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return None
