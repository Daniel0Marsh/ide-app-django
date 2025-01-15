import docker
import os
from django.utils import timezone
from user.models import DockerSession


class ProjectContainerManager:
    """
    Manage Docker containers for each user and their projects.
    """
    def __init__(self, project, user):
        self.project = project
        self.user = user
        self.container_name = f"{self.user.id}_container"
        self.project_path = user.project_dir
        self.client = docker.from_env()

    def get_container(self):
        """
        Retrieve the Docker container for the project from the model.
        """
        try:
            docker_session = DockerSession.objects.get(user=self.user)
            container = self.client.containers.get(docker_session.container_id)
            return container
        except DockerSession.DoesNotExist:
            return None
        except docker.errors.NotFound:
            return None

    def create_container(self):
        """
        Create a new Docker container for the user and store its session in the model.
        This includes the mounted volume for persistence.
        """
        # Define a path for the mounted volume to persist data on the host system
        volume_path = f'/mnt/{self.user.id}_volume'  # Use a directory that persists user data

        container = self.client.containers.run(
            image='terminal_session',  # Use your desired Docker image here
            name=self.container_name,
            volumes={self.project_path: {'bind': f'/{self.user}', 'mode': 'rw'},  # Mount user project directory
                     volume_path: {'bind': '/mnt', 'mode': 'rw'}},  # Persistent volume for file system
            working_dir=f'/{self.user}',
            stdin_open=True,
            tty=True,
            command='/bin/bash -l',
            detach=True,
            user=f"{os.getuid()}:{os.getgid()}",
            security_opt=["no-new-privileges"],
            read_only=False,
        )

        # Create and store a DockerSession in the database
        docker_session = DockerSession.objects.create(
            user=self.user,
            container_id=container.id,
            created_at=timezone.now(),
            status='running',
            mounted_volume=volume_path  # Store the mounted volume path in the model
        )

        return container

    def start_container(self):
        """
        Start the Docker container if it exists but is not running.
        """
        container = self.get_container()
        if container and container.status != "running":
            container.start()
        elif not container:
            container = self.create_container()
        return container

    def attach_container(self):
        """
        Attach to the container for real-time terminal interaction.
        We ensure the container is started, and we run a persistent shell.
        """
        container = self.start_container()

        # Check if an exec instance already exists, otherwise create one
        exec_id = container.exec_run(
            cmd=['/bin/bash', '-l'],  # Open a login shell to maintain the interactive session
            stdin=True,
            tty=True,
            detach=True,  # Detach so it can continue running in the background
        )

        # Attach to the exec instance
        return container.exec_start(exec_id.id, stdin=True, stdout=True, stderr=True, stream=True, logs=True)

    def execute_command(self, command):
        """
        Execute a given command in the container, ensuring it's done in an interactive shell session.
        """
        container = self.start_container()

        # Create a new exec instance, or reuse the existing one
        exec_instance = container.exec_run(
            cmd=['/bin/bash', '-c', command],
            stdout=True,
            stderr=True,
            stdin=True,
            tty=True
        )

        output = exec_instance.output.decode().strip()
        return {
            'formatted_output': output,
            'exit_code': exec_instance.exit_code
        }

    def stop_container(self):
        """
        Stop the Docker container if it's running and update the model status.
        """
        container = self.get_container()
        if container and container.status == "running":
            container.stop()
            docker_session = DockerSession.objects.get(user=self.user)
            docker_session.status = 'stopped'
            docker_session.save()

    def delete_container(self):
        """
        Delete the Docker container if it exists and update the model status.
        """
        container = self.get_container()
        if container:
            container.remove(force=True)
            docker_session = DockerSession.objects.get(user=self.user)
            docker_session.status = 'removed'
            docker_session.save()
