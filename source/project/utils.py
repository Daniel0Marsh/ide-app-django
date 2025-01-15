from threading import Timer
import docker
import os
from django.utils import timezone
from user.models import DockerSession


class ProjectContainerManager:
    """
    Manages Docker containers for user projects.
    """
    TIMEOUT_SECONDS = 3600  # Timeout duration (1 hour)

    def __init__(self, project, user):
        """
        Initializes the container manager with the project and user details.
        """
        self.project = project
        self.user = user
        self.container_name = f"{self.user.username}_{self.user.id}"
        self.project_path = user.project_dir
        self.client = docker.from_env()
        self.timeout_timer = None

    def get_container(self):
        """
        Retrieves the container associated with the user from the model.
        """
        try:
            docker_session = DockerSession.objects.get(user=self.user)
            return self.client.containers.get(docker_session.container_id)
        except (DockerSession.DoesNotExist, docker.errors.NotFound):
            return None

    def create_container(self):
        """
        Creates a new Docker container for the user and saves the session in the model.
        """
        volume_path = f'/mnt/{self.user.id}_volume'
        self._remove_existing_container()

        container = self.client.containers.run(
            image='terminal_session',
            name=self.container_name,
            volumes={
                self.project_path: {'bind': f'/{self.user}', 'mode': 'rw'},
                volume_path: {'bind': f'{self.project_path}/mnt', 'mode': 'rw'},
            },
            working_dir=f'/{self.user}',
            stdin_open=True,
            tty=True,
            command='/bin/bash -l',
            detach=True,
            user=f"{os.getuid()}:{os.getgid()}",
            security_opt=["no-new-privileges"],
            read_only=False,
            mem_limit=self.user.default_mem_limit,
            memswap_limit=self.user.default_memswap_limit,
            cpus=str(self.user.default_cpus),
            cpu_shares=self.user.default_cpu_shares,
        )

        DockerSession.objects.create(
            user=self.user,
            container_id=container.id,
            container_name=self.container_name,
            created_at=timezone.now(),
            status='running',
            mounted_volume=volume_path,
        )

        self._start_timeout_timer()
        return container

    def _remove_existing_container(self):
        """
        Removes any existing container with the same name.
        """
        try:
            existing_container = self.client.containers.get(self.container_name)
            existing_container.remove(force=True)
        except docker.errors.NotFound:
            pass

    def start_container(self):
        """
        Starts the container if it's not already running, or creates a new one.
        """
        container = self.get_container()
        if container and container.status != "running":
            container.start()
            DockerSession.objects.filter(user=self.user).update(status='running')
        elif not container:
            container = self.create_container()

        self._start_timeout_timer()
        return container

    def attach_container(self):
        """
        Attaches to the container for terminal interaction.
        """
        container = self.start_container()
        self._update_last_activity()
        return container

    def _update_last_activity(self):
        """
        Updates the last activity timestamp for the user's session.
        """
        DockerSession.objects.filter(user=self.user).update(last_activity_at=timezone.now())

    def _start_timeout_timer(self):
        """
        Starts or resets the timeout timer for the container session.
        """
        if self.timeout_timer:
            self.timeout_timer.cancel()

        self.timeout_timer = Timer(self.TIMEOUT_SECONDS, self._stop_container_due_to_timeout)
        self.timeout_timer.start()

    def _stop_container_due_to_timeout(self):
        """
        Stops the container if the session times out.
        """
        container = self.get_container()
        if container:
            container.stop()
            DockerSession.objects.filter(user=self.user).update(status='stopped')

    def execute_command(self, command):
        """
        Executes a command in the container and returns the output.
        """
        container = self.start_container()

        exec_instance = container.exec_run(
            cmd=['/bin/bash', '-c', command],
            stdout=True,
            stderr=True,
            stdin=True,
            tty=True
        )

        self._start_timeout_timer()

        return {
            'formatted_output': exec_instance.output.decode().strip(),
            'exit_code': exec_instance.exit_code
        }

    def delete_container(self):
        """
        Deletes the Docker container and updates the session status to 'removed'.
        """
        container = self.get_container()
        if container:
            container.remove(force=True)
            DockerSession.objects.filter(user=self.user).update(status='removed')

        if self.timeout_timer:
            self.timeout_timer.cancel()
