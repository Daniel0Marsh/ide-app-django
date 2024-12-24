from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from .models import Project
from django.http import HttpResponseRedirect, JsonResponse, Http404, HttpResponse
from django.urls import reverse
from django.conf import settings
import docker
import os
from django.http import FileResponse
import shutil
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime, timedelta
from django.utils.timezone import now



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


class IdeView(LoginRequiredMixin, TemplateView):
    template_name = 'ide.html'
    login_url = 'login'  # Redirect to the login page if not authenticated

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the project view.
        """
        project_id = kwargs.get('project_id')

        if project_id:
            try:
                current_project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return redirect('dashboard')  # Redirect if the project does not exist
        else:
            current_project = Project.objects.order_by('-modified_at').first()

        all_projects = Project.objects.all()
        project_tree = get_project_tree(current_project.project_path)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'project_tree': project_tree})

        context = {
            'all_projects': all_projects,
            'current_project': current_project,
            'project_tree': project_tree,
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
        project_path = project.project_path
        file_path = request.POST.get('file_path')

        if not file_path:
            # Redirect if no file path is provided
            return HttpResponseRedirect(reverse('ide', kwargs={'project_id': project.id}))

        if not os.path.exists(file_path):
            # Redirect if the file does not exist
            return HttpResponseRedirect(reverse('ide', kwargs={'project_id': project.id}))

        try:
            os.remove(file_path)  # Attempt to delete the file
        except OSError as e:
            # Log the error for debugging purposes (if logging is set up)
            print(f"Error deleting file {file_path}: {e}")

        # Redirect back to the IDE page regardless of success or failure
        return HttpResponseRedirect(reverse('ide', kwargs={'project_id': project.id}))


    def save_file(self, request, project):
        """
        Save, rename, or create a new file in the project and update project settings.
        """
        selected_theme = request.POST.get('selected_theme')
        selected_syntax = request.POST.get('selected_syntax')

        file_name = request.POST.get('file_name')
        file_content = request.POST.get('file_contents', '')
        file_path = request.POST.get('file_path')
        new_file_name = request.POST.get('new_file_name')

        # Fetch the current project
        project_path = project.project_path
        all_projects = Project.objects.all()

        if new_file_name:
            if file_path:
                # Rename an existing file
                directory = os.path.dirname(file_path)
                new_path = os.path.join(directory, new_file_name)
                os.rename(file_path, new_path)
                file_name = new_file_name
                file_path = new_path
            else:
                # Create a new file with the provided new file name
                new_path = os.path.join(project_path, new_file_name)
                file_name = new_file_name
                file_path = new_path
        elif file_path:
            # Save to an existing file
            new_path = file_path
        elif file_name:
            # Create a new file with the provided file name
            new_path = os.path.join(project_path, file_name)
        else:
            # Create a new file with a default name
            new_path = os.path.join(project_path, "new_file.txt")
            file_name = "new_file.txt"

        # Write content to the file
        try:
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
        except Exception as e:
            return HttpResponse(f"Error saving file: {e}", status=500)

        # Save theme and syntax settings
        if selected_theme and selected_syntax:
            project.selected_theme = selected_theme
            project.selected_syntax = selected_syntax
            project.last_modified_at = now()
            project.save()

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


    def download_project(self, request, project):
        """
        Create and return a zip file of the project's directory for download.
        """
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

        return response

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
    login_url = 'login'  # Redirect to the login page if not authenticated


    def get(self, request):
        """
        Render the dashboard with a list of the user's projects and activities.
        """
        # Get projects related to the currently logged-in user
        user_projects = Project.objects.filter(user=request.user)
        recent_activities, days = self.user_activity(user_projects)

        context = {
            'user_projects': user_projects,
            'recent_activities': recent_activities,
            'activity_days': days
        }
        return render(request, self.template_name, context)

    def post(self, request):
        """
        Handle actions such as opening, deleting, or creating a project.
        """
        action_map = {
            'open_project': self.open_project,
            'delete_project': self.delete_project,
            'create_project': self.create_project,
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)
        return HttpResponse("Invalid action", status=400)


    def user_activity(self, user_projects):
        """
        Retrieve the 5 most recent activities and the activity data for the past year
        based on the modified_at field of user projects.
        """
        # Get the 5 most recent activities based on the modified_at field
        recent_activities = user_projects.order_by('-modified_at')[:5]

        # Generate activity data for the past year
        start_date = now() - timedelta(days=365)
        end_date = now()
        activities = user_projects.filter(modified_at__range=(start_date, end_date))

        # Create a dictionary to count activities per day
        activity_data = {}
        for activity in activities:
            day = activity.modified_at.date()
            activity_data[day] = activity_data.get(day, 0) + 1

        # Generate a list of activity data for each day in the past year
        days = [
            {'date': current_date, 'count': activity_data.get(current_date.date(), 0)}
            for current_date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1))
        ]

        return recent_activities, days


    def open_project(self, request):
        """
        Open a project by redirecting to the IDE view.
        """
        project_id = request.POST.get('project_id')
        if not project_id:
            return HttpResponse("Project ID not provided", status=400)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return HttpResponse("Project not found", status=404)

        return redirect('ide', project_id=project.id)


    def delete_project(self, request):
        """
        Delete a project, its associated files, and its Docker container.
        """
        project_id = request.POST.get('project_id')
        if not project_id:
            return HttpResponse("Project ID not provided", status=400)

        try:
            # Fetch the project from the database
            project = Project.objects.get(id=project_id)

            # Delete the Docker container associated with the project
            container_manager = ProjectContainerManager(project)
            container_manager.delete_container()  # Delete the container if it exists

            # Delete the project directory
            shutil.rmtree(project.project_path)  # Remove the project's directory

            # Delete the project from the database
            project.delete()

        except Project.DoesNotExist:
            return HttpResponse("Project not found", status=404)
        except Exception as e:
            return HttpResponse(f"Error deleting project: {e}", status=500)

        # After deletion, determine the current project and render the updated dashboard
        user_projects = Project.objects.all()
        current_project = Project.objects.order_by('-modified_at').first()
        recent_activities, days = self.user_activity(user_projects)

        context = {
            'user_projects': user_projects,
            'recent_activities': recent_activities,
            'activity_days': days
        }

        # If there's a current project, fetch and add the project tree
        if current_project:
            context['project_tree'] = get_project_tree(current_project.project_path)

        return render(request, self.template_name, context)


    def create_project(self, request):
        """
        Create a new project and redirect to the IDE view.
        """
        project_name = request.POST.get('project_name')
        project_description = request.POST.get('project_description')

        if not project_name:
            return HttpResponse("Project name is required", status=400)

        # Define the base directory for projects
        default_project_path = os.path.join(settings.BASE_DIR, "UserProjects")
        project_path = os.path.join(default_project_path, project_name)

        try:
            # Create the project directory
            os.makedirs(project_path, exist_ok=True)

            # Save the project to the database with the user as the owner
            current_project = Project(
                project_name=project_name,
                project_description=project_description,
                project_path=project_path,
                user=request.user  # Associate the project with the logged-in user
            )
            current_project.save()
        except Exception as e:
            return HttpResponse(f"Error creating project: {e}", status=500)

        # Redirect to the IDE view for the new project
        return redirect('ide', project_id=current_project.id)


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
                '/host/path/.bash_history': {'bind': '/root/.bash_history', 'mode': 'rw'}
            },
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
