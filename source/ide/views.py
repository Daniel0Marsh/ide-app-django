from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.conf import settings
from django.http import FileResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.shortcuts import redirect
from .models import Project, Task
from user_profile.views import add_activity_to_log
from chat.models import ChatRoom, Message
import docker
import os
import shutil
import markdown


def get_project_tree(project_path):
    project_tree = []
    root_dir = os.path.basename(project_path)
    for root, dirs, files in os.walk(project_path):
        relative_path = os.path.relpath(root, project_path)
        if relative_path == '.':
            relative_path = ''
        node = {
            'name': root_dir if relative_path == '' else os.path.join(root_dir, relative_path),
            'type': 'directory',
            'children': []
        }
        for file in files:
            file_path = os.path.join(root, file)
            node['children'].append({
                'name': file,
                'type': 'file',
                'path': file_path
            })
        project_tree.append(node)
    return project_tree


def update_task(request, project):
    """
    Handle updating tasks for a project.
    """
    task_id = request.POST.get('task_id')
    title = request.POST.get('task_title')
    description = request.POST.get('task_description')
    status = request.POST.get('task_status')

    # Fetch the task
    task = get_object_or_404(Task, id=task_id, project=project)

    # Update the task
    task.title = title
    task.description = description
    task.status = status
    task.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))


class ProjectView(TemplateView):
    template_name = 'project.html'

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the project view.
        """
        project_id = kwargs.get('project_id')

        # Fetch the project by its ID or get the latest modified project
        if project_id:
            try:
                current_project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return redirect('personal_profile')  # Redirect if the project does not exist
        else:
            current_project = Project.objects.order_by('-modified_at').first()

        project_tree = get_project_tree(current_project.project_path)

        # Read the README.md file content
        readme_content = "<p>No README file available.</p>"
        readme_path = os.path.join(current_project.project_path, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as readme_file:
                readme_content = markdown.markdown(readme_file.read())

        # Default empty lists for guests or unauthenticated users
        following_users = []
        followers_users = []
        chat_rooms = []
        all_users = []

        # If the user is authenticated, fetch the relevant data
        if isinstance(request.user, AnonymousUser):
            # For unauthenticated users, no user-specific data
            pass
        else:
            # For authenticated users, fetch the user's following and followers
            following_users = request.user.following.all()
            followers_users = request.user.followers.all()

            # For chat-related logic, fetch the user's chat rooms
            chat_rooms = ChatRoom.objects.filter(participants=request.user)

            # Merge the following and followers lists
            all_users = (following_users | followers_users).distinct()

        # Pass the context to the template
        context = {
            'current_project': current_project,
            'project_tree': project_tree,
            'readme_content': readme_content,
            'tasks': current_project.tasks.all(),
            'recent_chats': chat_rooms,
            'all_users': all_users,
            'all_messages': Message.objects.filter(room__in=chat_rooms).order_by('timestamp'),
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for various project actions.
        """
        project_id = kwargs.get('project_id')

        if not project_id:
            return HttpResponse("Project not found", status=404)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return HttpResponse("Project not found", status=404)

        action_map = {
            'add_collaborator': self.add_collaborator,
            'edit_project_details': self.edit_project_details,
            'delete': self.delete_project,
            'remove_collaborator': self.remove_collaborator,
            'toggle_like': self.toggle_like,
            'add_task': self.add_task,
            'update_task': update_task,
        }

        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request, project)  # Pass project to the action method

        return HttpResponse("Invalid action", status=400)

    @staticmethod
    def toggle_like(request, project):
        if request.user in project.liked_by.all():
            project.liked_by.remove(request.user)
            project.likes -= 1
        else:
            project.liked_by.add(request.user)
            project.likes += 1
        project.save()
        return redirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def add_task(request, project):
        """
        Handle assigning tasks for a project.
        """
        title = request.POST['title']
        description = request.POST.get('description', '')
        assigned_to_id = request.POST['assigned_to']
        assigned_to = get_object_or_404(get_user_model(), id=assigned_to_id)

        # Create the task
        Task.objects.create(
            project=project,
            assigned_to=assigned_to,
            assigned_by=request.user,
            title=title,
            description=description,
            status='not_started'
        )
        return redirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def add_collaborator(request, project):
        """
        Handle adding a collaborator to a project.
        """
        user = request.user  # Get the user who is adding the collaborator
        project_name = project.project_name  # Get the project name
        collaborator_username = request.POST.get('username')

        try:
            # Query the user model directly
            User = get_user_model()
            collaborator = User.objects.get(username=collaborator_username)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)

        # Add collaborator
        project.collaborators.add(collaborator)

        # Log the activity
        action = f"Added {collaborator_username} as a collaborator to the project"
        add_activity_to_log(user, project_name, action)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def remove_collaborator(request, project):
        """
        Handle removing a collaborator from a project.
        """
        user = request.user  # Get the user who is removing the collaborator
        project_name = project.project_name  # Get the project name
        collaborator_id = request.POST.get('collaborator_id')

        try:
            # Query the user model directly
            User = get_user_model()
            collaborator = User.objects.get(id=collaborator_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)

        # Remove collaborator
        if collaborator in project.collaborators.all():
            project.collaborators.remove(collaborator)

            # Log the activity
            action = f"Removed {collaborator.username} from the collaborators of the project"
            add_activity_to_log(user, project_name, action)

            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        else:
            return JsonResponse({'error': 'User is not a collaborator'}, status=400)

    @staticmethod
    def edit_project_details(request, project):
        """
        Handle the updating of both project name, project description, and project visibility.
        """
        user = request.user  # Get the user who made the changes
        project_name = project.project_name  # Get the current project name
        new_name = request.POST.get('name')
        new_description = request.POST.get('description')
        is_public = 'is_public' in request.POST  # Check if the visibility checkbox is ticked (True) or not (False)

        if not new_name or not new_description:
            return HttpResponseBadRequest("Name and description cannot be empty")

        try:
            action = ''  # Initialize action string

            # Check if the project name has changed
            if project.project_name != new_name:
                # Rename the project directory
                old_project_path = project.project_path
                new_project_path = os.path.join(settings.BASE_DIR, "UserProjects", new_name)

                # Rename the directory
                os.rename(old_project_path, new_project_path)

                # Update the project path in the database
                project.project_path = new_project_path
                action = f"Renamed project from {project_name} to {new_name}"  # Action for renaming

            # Update the project name, description, and visibility
            project.project_name = new_name
            project.project_description = new_description
            project.is_public = is_public  # Update visibility based on checkbox
            project.save()

            # Log the activity for updating project details
            add_activity_to_log(user, project_name, action if action else f"Updated project details for {new_name}")

            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        except Project.DoesNotExist:
            return HttpResponseBadRequest("Project not found")
        except Exception as e:
            return HttpResponseBadRequest(f"Error updating project: {e}")

    @staticmethod
    def delete_project(request, project):
        """
        Delete a project, its associated files, and its Docker container.
        """

        try:
            # Delete the Docker container associated with the project
            container_manager = ProjectContainerManager(project)
            container_manager.delete_container()  # Delete the container if it exists

            # Delete the project directory
            shutil.rmtree(project.project_path)  # Remove the project's directory

            # add deletion of the project to the users activity log
            user = request.user
            project_name = project.project_name
            action = 'Deleted Project'
            add_activity_to_log(user, project_name, action)

            # Delete the project from the database
            project.delete()

        except Project.DoesNotExist:
            return HttpResponse("Project not found", status=404)
        except Exception as e:
            return HttpResponse(f"Error deleting project: {e}", status=500)

        return redirect('personal_profile')


class IdeView(LoginRequiredMixin, TemplateView):
    template_name = 'ide.html'
    login_url = 'login'  # Redirect to the login page if not authenticated

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the IDE view.
        """
        project_id = kwargs.get('project_id')

        if project_id:
            try:
                current_project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return redirect('personal_profile')  # Redirect if the project does not exist
        else:
            current_project = Project.objects.order_by('-modified_at').first()

        if not current_project:
            return redirect('personal_profile')  # Handle the case where no projects exist

        # Ensure README.md file exists
        readme_path = os.path.join(current_project.project_path, 'README.md')
        if not os.path.exists(readme_path):
            with open(readme_path, 'w', encoding='utf-8') as file:
                file.write("# Welcome to your project\n\nThis is the README.md file for your project.")

        # Read the README.md file content
        try:
            with open(readme_path, 'r', encoding='utf-8') as file:
                readme_content = file.read()
        except Exception as e:
            return HttpResponse(f"Error reading README.md: {e}", status=500)

        all_projects = Project.objects.all()
        project_tree = get_project_tree(current_project.project_path)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'project_tree': project_tree})

        # Get a list of users the logged-in user is following and is being followed by
        following_users = request.user.following.all()
        followers_users = request.user.followers.all()

        # required data for messages and chat logic
        chat_rooms = ChatRoom.objects.filter(participants=request.user)

        context = {
            'all_projects': all_projects,
            'current_project': current_project,
            'project_tree': project_tree,
            'file_name': 'README.md',
            'file_path': readme_path,
            'file_content': readme_content,
            'tasks': current_project.tasks.all(),
            'recent_chats': ChatRoom.objects.filter(participants=request.user),
            'all_users': (following_users | followers_users).distinct(),
            'all_messages': Message.objects.filter(room__in=chat_rooms).order_by('timestamp'),
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for various project actions.
        """
        project_id = kwargs.get('project_id')

        if not project_id:
            return HttpResponse("Project not found", status=404)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return HttpResponse("Project not found", status=404)

        action_map = {
            'delete': self.delete,
            'save_file': self.save_file,
            'rename_file': self.save_file,
            'open_file': self.open_file,
            'prompt': self.prompt,
            'download_project': self.download_project,
            'update_theme': self.update_theme,
            'update_task': update_task,
        }

        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request, project)

        return HttpResponse("Invalid action", status=400)

    def prompt(self, request, project):
        """
        Execute a command in the project's Docker container.
        """
        prompt = request.POST.get('prompt')
        if not prompt:
            return JsonResponse({'response': ''}, status=400)

        manager = ProjectContainerManager(project)

        try:
            # Execute the command using the method in ProjectContainerManager
            response_output = manager.execute_command(prompt)

            # Return the response
            if response_output['exit_code'] != 0:
                return JsonResponse({'response': response_output['formatted_output']}, status=500)

            return JsonResponse({'response': response_output['formatted_output']}, status=200)

        except Exception as e:
            return JsonResponse({'response': str(e)}, status=500)

    @staticmethod
    def update_theme(request, project):
        """
        updates the theme and syntax on a project.
        """
        # Save theme and syntax settings

        selected_theme = request.POST.get('selected_theme', 'default_theme')
        selected_syntax = request.POST.get('selected_syntax', 'default_syntax')

        project.selected_theme = selected_theme
        project.selected_syntax = selected_syntax
        project.last_modified_at = now()
        project.save()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def open_file(self, request, project):
        """
        Open a file within the specified project and return its content.
        """
        file_path = request.POST.get('open_file')

        if not file_path:
            return HttpResponse("File path not provided", status=400)

        if not os.path.exists(file_path):
            return HttpResponse("File not found", status=404)

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
        except Exception as e:
            return HttpResponse(f"Error reading file: {e}", status=500)

        context = {
            'current_project': project,
            'file_name': os.path.basename(file_path),
            'file_path': file_path,
            'file_content': file_content,
            'project_tree': get_project_tree(project.project_path),
        }

        return render(request, self.template_name, context)

    @staticmethod
    def delete(request, project):
        """
        Delete a specified file from the project.
        """
        user = request.user  # Get the user who initiated the delete action
        project_name = project.project_name  # Get the project name
        file_path = request.POST.get('file_path')

        if not file_path:
            # Redirect if no file path is provided
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        if not os.path.exists(file_path):
            # Redirect if the file does not exist
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        try:
            # Attempt to delete the file
            os.remove(file_path)
            action = f"Deleted file {os.path.basename(file_path)}"  # Action to log after successful file deletion
        except OSError as e:
            # Log the error for debugging purposes (if logging is set up)
            print(f"Error deleting file {file_path}: {e}")
            action = f"Failed to delete file {file_path}"  # Log failure if deletion fails

        # Log the activity (whether the deletion was successful or not)
        add_activity_to_log(user, project_name, action)

        # Redirect back to the IDE page regardless of success or failure
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def save_file(self, request, project):
        """
        Save, rename, or create a new file in the project and update project settings.
        """
        user = request.user  # Get the user who made the change
        project_name = project.project_name  # Get the project name

        file_name = request.POST.get('file_name')
        file_content = request.POST.get('file_contents', '')
        file_path = request.POST.get('file_path')
        new_file_name = request.POST.get('new_file_name')

        # Fetch the current project
        project_path = project.project_path
        all_projects = Project.objects.all()

        action = ''  # Initialize action string

        if new_file_name:
            if file_path:
                # Rename an existing file
                directory = os.path.dirname(file_path)
                new_path = os.path.join(directory, new_file_name)
                os.rename(file_path, new_path)
                file_name = new_file_name
                file_path = new_path
                action = f"Renamed file {file_name} to {new_file_name}"
            else:
                # Create a new file with the provided new file name
                new_path = os.path.join(project_path, new_file_name)
                file_name = new_file_name
                file_path = new_path
                action = f"Created a new file {new_file_name}"
        elif file_path:
            # Save to an existing file
            new_path = file_path
            action = f"Saved changes to file {file_name}"
        elif file_name:
            # Create a new file with the provided file name
            new_path = os.path.join(project_path, file_name)
            action = f"Created a new file {file_name}"
        else:
            # Create a new file with a default name
            new_path = os.path.join(project_path, "new_file.txt")
            file_name = "new_file.txt"
            action = "Created a new file new_file.txt"

        # Write content to the file
        try:
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
        except Exception as e:
            return HttpResponse(f"Error saving file: {e}", status=500)

        # Log the activity
        add_activity_to_log(user, project_name, action)

        context = {
            'all_projects': all_projects,
            'current_project': project,
            'file_name': file_name,
            'file_path': new_path,
            'file_content': file_content,
            'project_tree': get_project_tree(project_path),
        }

        # Render the IDE view with the updated file information
        return render(request, self.template_name, context)

    @staticmethod
    def download_project(request, project):
        """
        Create and return a zip file of the project's directory for download.
        """
        user = request.user  # Get the user who initiated the download
        project_name = project.project_name  # Get the project name
        action = f"Downloaded the project {project_name}"  # Action to log

        project_path = project.project_path

        # Extract the project directory name
        directory_name = os.path.basename(project_path)

        # Temporary path for the zip file
        zip_file_path = os.path.join("/tmp", f"{directory_name}.zip")

        try:
            # Create the zip archive
            shutil.make_archive(zip_file_path[:-4], 'zip', project_path)

            # Serve the zip file as a downloadable response
            with open(zip_file_path, 'rb') as zip_file:
                response = FileResponse(zip_file, as_attachment=True)
                response['Content-Disposition'] = f'attachment; filename="{directory_name}.zip"'
        except Exception as e:
            return HttpResponse(f"Error creating zip file: {e}", status=500)
        finally:
            # Remove the temporary zip file
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)

        # Log the activity
        add_activity_to_log(user, project_name, action)

        return response


class ProjectContainerManager:
    """
    Manage Docker containers for each project.
    """

    def __init__(self, project):
        self.project = project
        self.project_name = os.path.basename(project.project_path)
        self.container_name = f"{self.project_name}_container"
        self.project_path = project.project_path
        self.client = docker.from_env()

    def get_container(self):
        """
        Retrieve the Docker container for the project.
        """
        try:
            return self.client.containers.get(self.container_name)
        except docker.errors.NotFound:
            return None

    def create_container(self):
        """
        Create a new Docker container for the project.
        """
        return self.client.containers.run(
            image='terminal_session',
            name=self.container_name,
            volumes={
                self.project_path: {'bind': f'/{self.project_name}', 'mode': 'rw'},
                '/host/path/.bash_history': {'bind': '/root/.bash_history', 'mode': 'rw'}},
            working_dir=f'/{self.project_name}',
            stdin_open=True,
            tty=True,
            command='/bin/bash -l',
            detach=True,
            user=f"{os.getuid()}:{os.getgid()}",
            security_opt=["no-new-privileges"],
            read_only=False,
        )

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
        """
        container = self.start_container()
        return container.attach(stdin=True, stdout=True, stderr=True, stream=True, logs=True)

    def execute_command(self, command):
        """
        Execute a given command in the container.
        """
        container = self.start_container()
        try:
            response = container.exec_run(
                cmd=['/bin/bash', '-c', command],
                stdout=True,
                stderr=True,
                stdin=True,
                tty=True
            )
            output = response.output.decode().strip()
            return {
                'formatted_output': output,
                'exit_code': response.exit_code
            }
        except Exception as e:
            raise RuntimeError(f"Error executing command: {str(e)}")

    def stop_container(self):
        """
        Stop the Docker container if it's running.
        """
        container = self.get_container()
        if container and container.status == "running":
            container.stop()

    def delete_container(self):
        """
        Delete the Docker container if it exists.
        """
        container = self.get_container()
        if container:
            container.remove(force=True)
