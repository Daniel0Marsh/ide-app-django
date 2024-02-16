from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Project
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.urls import reverse
from django.conf import settings
import docker
import os
from django.http import FileResponse
import shutil

class IdeView(TemplateView):
    template_name = 'ide.html'

    def get_project_tree(self, project_path):
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

    def get(self, request):
        all_projects = Project.objects.all()
        current_project = Project.objects.order_by('-modified_at').first()
        if current_project:
            context = {
                'all_projects': all_projects,
                'current_project': current_project,
                'project_tree': self.get_project_tree(current_project.project_path)
            }
        else:
            context = {
                'all_projects': all_projects,
                'current_project': "none",
            }
        return render(request, self.template_name, context)

    def post(self, request):
        action_map = {
            'delete': self.delete,
            'save_file': self.save_file,
            'rename_file': self.save_file,
            'open_file': self.open_file,
            'prompt': self.prompt,
            'open_project': self.open_project,
            'create_project': self.create_project,
            'download_project': self. download_project
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)

    def prompt(self, request):
        current_project = Project.objects.first()
        project_name = current_project.project_name
        project_path = current_project.project_path
        file_path = os.path.join(project_path, project_name)
        prompt = request.POST.get('prompt')

        try:
            client = docker.from_env()
            container_name = f"{project_name}_container"

            try:
                existing_container = client.containers.get(container_name)
            except docker.errors.NotFound:
                existing_container = None

            if not existing_container:
                existing_container = client.containers.run(
                    image='terminal_session',
                    name=container_name,
                    volumes={project_path: {'bind': '/projects', 'mode': 'rw'}},
                    working_dir='/projects',
                    stdin_open=True,
                    tty=True,
                    command='/bin/bash',
                    detach=True
                )

            response = existing_container.exec_run(
                cmd=['/bin/bash', '-c', prompt],
                stdout=True,
                stderr=True
            )

            response_output = response.output.decode().strip()  # Strip whitespace from response

            if response_output:  # Check if response is not empty
                return JsonResponse({'response': response_output},
                                    status=response.exit_code if 100 <= response.exit_code <= 599 else 500)
            else:
                return JsonResponse({'response': 'No output from terminal.'}, status=200)

        except Exception as e:
            return JsonResponse({'response': str(e)}, status=500)

    def open_file(self, request):
        all_projects = Project.objects.all()
        current_project = Project.objects.first()
        project_path = current_project.project_path
        file_name = request.POST.get('open_file')
        file_path = request.POST.get('file_path')

        # Check if the file exists
        if os.path.exists(file_path):
            # Read the file content
            with open(file_path, 'r+') as f:
                file_content = f.read()

            context = {
                'all_projects': all_projects,
                'current_project': current_project,
                'file_name': file_name,
                'file_path': file_path,
                'file_content': file_content,
                'project_tree': self.get_project_tree(project_path)
            }
            return render(request, self.template_name, context)
        else:
            # Handle case where file doesn't exist
            return HttpResponse("File not found", status=404)

    @staticmethod
    def delete(request):
        project_id = request.POST.get('project_id')
        current_project = Project.objects.get(id=project_id)

        project_path = current_project.project_path
        file_path = request.POST.get('file_path')

        # Check if the file exists
        if os.path.exists(file_path):
            # Delete the file
            os.remove(file_path)
            return HttpResponseRedirect(reverse('project'))
        else:
            # Handle case where file doesn't exist
            return HttpResponseRedirect(reverse('project'))

        return HttpResponseRedirect(reverse('project'))

    def save_file(self, request):
        project_id = request.POST.get('project_id')
        selected_theme = request.POST.get('selected_theme')
        selected_syntax = request.POST.get('selected_syntax')

        file_name = request.POST.get('file_name')
        file_content = request.POST.get('file_contents')
        file_path = request.POST.get('file_path')
        new_file_name = request.POST.get('new_file_name')

        current_project = Project.objects.get(id=project_id)
        project_path = current_project.project_path
        all_projects = Project.objects.all()

        if new_file_name and file_path:
            # change file name here
            directory, old_file_name = os.path.split(file_path)
            path = os.path.join(directory, new_file_name)
            file_name = new_file_name

        elif new_file_name and not file_path:
            # create new file with new_file_name
            path = os.path.join(project_path, new_file_name)
            file_name = new_file_name

        elif file_name and file_path:
            # save file
            path = os.path.join(file_path)

        elif file_name and not file_path:
            # create new file with file_name
            path = os.path.join(project_path, file_name)

        else:
            # careate new file with "New_file.txt" as name
            path = os.path.join(project_path, "New_file.txt")
            file_name = "New_file.txt"

        with open(path, 'w') as f:
            f.write(file_content)

        if selected_theme and selected_theme:
            # Update selected_theme and selected_syntax in the model
            current_project.selected_theme = selected_theme
            current_project.selected_syntax = selected_syntax
            current_project.save()

        context = {
            'all_projects': all_projects,
            'current_project': current_project,
            'file_name': file_name,
            'file_path': path,
            'file_content': file_content,
            'project_tree': self.get_project_tree(project_path)
        }
        return render(request, self.template_name, context)

    def open_project(self, request):
        project_id = request.POST.get('project_id')
        all_projects = Project.objects.all()

        current_project = Project.objects.get(id=project_id)
        project_path = current_project.project_path

        context = {
            'all_projects': all_projects,
            'current_project': current_project,
            'project_tree': self.get_project_tree(project_path)
        }
        return render(request, self.template_name, context)

    def create_project(self, request):
        all_projects = Project.objects.all()
        project_name = request.POST.get('project_name')
        project_description = request.POST.get('project_description')

        # Define the path where projects will be stored
        default_project_path = os.path.join(settings.BASE_DIR, "UserProjects")

        # Create the project directory if it doesn't exist
        project_path = os.path.join(default_project_path, project_name)
        os.makedirs(project_path, exist_ok=True)

        # Create and save the project instance
        current_project = Project(
            project_name=project_name,
            project_description=project_description,
            project_path=project_path
        )
        current_project.save()

        # Prepare the context for rendering
        project_path = current_project.project_path
        context = {
            'all_projects': all_projects,
            'current_project': current_project,
            'project_tree': self.get_project_tree(project_path)
        }
        return render(request, self.template_name, context)

    def download_project(self, request):
        project_id = request.POST.get('project_id')
        current_project = Project.objects.get(id=project_id)
        project_path = current_project.project_path

        # Extract the directory name from the path
        directory_name = os.path.basename(project_path)

        # Create a zip file of the directory
        zip_file_path = os.path.join("/tmp", f"{directory_name}.zip")  # Save the zip file temporarily
        shutil.make_archive(zip_file_path[:-4], 'zip', project_path)

        # Create a FileResponse with the zip file
        response = FileResponse(open(zip_file_path, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{directory_name}.zip"'

        # Remove the temporary zip file
        os.remove(zip_file_path)
        return response
