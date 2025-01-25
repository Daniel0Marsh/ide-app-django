import hashlib
from threading import Timer
import docker
import os
import re
import base64
from github import Github
from github import InputGitTreeElement

from django.contrib import messages
from django.http import HttpResponseRedirect
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


class GitHubUtils:

    @staticmethod
    def get_github_account(request):
        """Retrieve GitHub account and token."""
        github_account = request.user.social_auth.filter(provider='github').first()
        if not github_account:
            return GitHubUtils._redirect_with_error(request, "GitHub account is not connected. Please link your account.")
        token = github_account.extra_data.get('access_token')
        if not token:
            return GitHubUtils._redirect_with_error(request, "GitHub access token is missing. Please authorize the app.")
        return Github(token), Github(token).get_user()

    @staticmethod
    def get_repo(request, project):
        """
        gets the GitHub token key for the repository
        """
        git_token, _ = GitHubUtils.get_github_account(request)
        repo_name = re.search(r"github\.com/([^/]+/[^/]+)", project.repository).group(1)
        return git_token.get_repo(repo_name)

    @staticmethod
    def get_current_branch(request, project):
        """
        gets the current branch for the project
        """
        if bool(project.repository):
            try:
                repo = GitHubUtils.get_repo(request, project)
                branch = repo.get_branch(repo.default_branch)
                return branch.name
            except Exception as e:
                messages.error(request, f"Error fetching branch: {e}")
        else:
            messages.error(request, f"GitHub account is not connected. Please link your account.")

    @staticmethod
    def _redirect_with_error(request, message):
        """
        redirect to previous page with an error message
        """
        messages.error(request, message)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def get_local_files(project_path):
        """Retrieve a list of local files excluding dot files."""
        return [
            {'change_type': 'new', 'file': os.path.relpath(os.path.join(root, file), project_path)}
            for root, dirs, files in os.walk(project_path)
            for file in files if
            not file.startswith('.') and not dirs[:][:].append(d for d in dirs if not d.startswith('.'))
        ]

    @staticmethod
    def get_uncommitted_files(request, project):
        """Fetch uncommitted files by comparing local files with GitHub repository."""
        local_files = GitHubUtils.get_local_files(project.project_path)
        local_files_dict = {file['file']: file for file in local_files}

        try:
            github_client, _ = GitHubUtils.get_github_account(request)
            repo = GitHubUtils.get_repo(request, project)
            github_contents = {content.path: content.sha for content in repo.get_contents("")}

            uncommitted_files = [
                                    {'file': file, 'change_type': 'Untracked'}
                                    for file in local_files_dict if file not in github_contents
                                ] + [
                                    {'file': file, 'change_type': 'Modified'}
                                    for file, content in local_files_dict.items()
                                    if hashlib.sha1(
                    f"blob {os.path.getsize(os.path.join(project.project_path, file))}\0".encode() + open(
                        os.path.join(project.project_path, file), 'rb').read()).hexdigest() != github_contents.get(file,
                                                                                                                   '')
                                ]

            deleted_files = set(github_contents) - set(local_files_dict)
            uncommitted_files.extend({'file': file, 'change_type': 'Deleted'} for file in deleted_files)

            return uncommitted_files
        except Exception as e:
            messages.error(request, f"Something went wrong while fetching your project files: {e}")

    @staticmethod
    def create_git_repo(request, project):
        """Create and initialize a GitHub repository with a README file."""
        try:
            git_token, git_user = GitHubUtils.get_github_account(request)
            repo = git_user.create_repo(
                name=request.POST['repo_name'],
                description=request.POST['repo_description'],
                private=not bool(request.POST.get('repo_public', False)),
                auto_init=False
            )
            with open(os.path.join(project.project_path, "README.md")) as f:
                repo.create_file("README.md", "Initial commit", f.read(), branch="main")

            project.repository, project.project_description, project.is_public = repo.html_url, repo.description, repo.private
            project.save()
            messages.success(request, "Your GitHub repository has been created successfully!")
        except Exception as e:
            messages.error(request, f"Oops! There was an issue creating your GitHub repository: {e}")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def commit_files(request, project, commit_push=True):
        """Commit multiple files to a GitHub repository."""
        commit_message = request.POST.get('commit_message')
        selected_files = request.POST.getlist('selected_files')
        commit_push_files = request.POST.get('commit_push_files')

        if not selected_files:
            messages.error(request, f"You have not selected any files to commit!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        try:
            repo = GitHubUtils.get_repo(request, project)
            latest_commit = repo.get_git_commit(repo.get_git_ref("heads/main").object.sha)
            base_tree = latest_commit.tree

            # Create new tree with the files
            elements = [
                InputGitTreeElement(
                    path=file_path,
                    mode="100644",
                    type="blob",
                    sha=repo.create_git_blob(open(os.path.join(project.project_path, file_path), "r").read(), "utf-8").sha
                ) for file_path in selected_files
            ]

            new_tree = repo.create_git_tree(elements, base_tree)
            new_commit = repo.create_git_commit(commit_message, new_tree, [latest_commit])
            repo.get_git_ref("heads/main").edit(new_commit.sha)

            if commit_push_files:
                GitHubUtils.push_all_commits(request, project)

            messages.success(request, "Your changes have been committed successfully!")

        except Exception as e:
            messages.error(request, f"Something went wrong while committing your files: {e}")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def push_all_commits(request, project):
        """Push all local commits to the specified branch on GitHub."""
        try:
            branch = GitHubUtils.get_current_branch(request, project)
            repo = GitHubUtils.get_repo(request, project)

            # Get current and remote commit references
            remote_ref = f"heads/{branch}"
            local_ref = f"heads/{branch}"

            remote_commit = repo.get_git_commit(repo.get_git_ref(remote_ref).object.sha)
            local_commit = repo.get_git_commit(repo.get_git_ref(local_ref).object.sha)

            # Compare commits to ensure local is ahead of remote
            if remote_commit.sha != local_commit.sha:
                messages.error(
                    request,
                    f"Please update your {branch} branch by pulling the latest changes before pushing."
                )
                return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

            # Push the local commit to the remote branch
            repo.get_git_ref(remote_ref).edit(local_commit.sha)
            messages.success(request, f"Your changes have been successfully pushed to the {branch} branch!")

        except Exception as e:
            messages.error(request, f"Failed to push your changes: {e}")

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    @staticmethod
    def pull_and_update_files(request, project):
        """Pull and update project files from GitHub."""
        try:
            repo = GitHubUtils.get_repo(request, project)
            current_branch = GitHubUtils.get_current_branch(request, project)
            local_files = GitHubUtils.get_local_files(project.project_path)

            for file_info in local_files:
                file_path = file_info['file']
                try:
                    github_file = repo.get_contents(file_path, ref=current_branch)
                    if github_file:
                        file_path_full = os.path.join(project.project_path, file_path)

                        # Decode base64 content if it's not already decoded
                        file_content = base64.b64decode(github_file.content).decode('utf-8')

                        # Write the decoded content to the local file
                        with open(file_path_full, 'w', encoding='utf-8') as f:
                            f.write(file_content)
                        file_info['change_type'] = 'updated'
                except Exception as e:
                    messages.error(request, f"Error pulling {file_path}: {e}")
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

            messages.success(request, "Project files updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating project files: {e}")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def manage_branch(request, project):
        branch_name = request.POST.get('branch_name')

        if 'create_new' in request.POST:
            GitHubUtils.switch_or_create_branch(request, project, branch_name, create_new=True)
        elif 'set_remote' in request.POST:
            GitHubUtils.set_remote_branch(request, project, branch_name)
        else:
            GitHubUtils.switch_or_create_branch(request, project, branch_name, create_new=False)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def switch_or_create_branch(request, project, branch_name, create_new=False):
        """
        Switch to an existing branch or create a new one.
        """
        try:
            repo = GitHubUtils.get_repo(request, project)
            branch_exists = lambda: repo.get_branch(branch_name)

            if create_new:
                try:
                    branch_exists()
                    return GitHubUtils._redirect_with_error(
                        request, f"Branch '{branch_name}' already exists."
                    )
                except Exception:  # Branch doesn't exist, proceed to create it
                    repo.create_git_ref(
                        ref=f"refs/heads/{branch_name}",
                        sha=repo.get_branch(repo.default_branch).commit.sha
                    )
                    messages.success(request, f"Branch '{branch_name}' created successfully.")
            else:
                if branch_exists():
                    messages.success(request, f"Switched to branch '{branch_name}'.")
                else:
                    return GitHubUtils._redirect_with_error(
                        request, f"Branch '{branch_name}' does not exist. Please create it first."
                    )
        except Exception as e:
            messages.error(request, f"Error switching or creating branch: {e}")

    @staticmethod
    def set_remote_branch(request, project, branch_name):
        """
        Set or update the remote branch reference for the repository.
        """
        try:
            repo = GitHubUtils.get_repo(request, project)
            repo.get_branch(branch_name)

            # Set the remote reference
            branch_sha = repo.get_branch(branch_name).commit.sha
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=branch_sha)

            messages.success(request, f"Remote branch '{branch_name}' set successfully.")

        except Exception as e:
            messages.error(request, f"Error setting remote branch: {e}")

