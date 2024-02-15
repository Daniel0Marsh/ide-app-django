from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Project
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.urls import reverse
from django.conf import settings
import docker
import os

class IdeView(TemplateView):
    template_name = 'ide.html'

    import os

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
                relative_file_path = os.path.join(relative_path, file)
                node['children'].append({
                    'name': file,
                    'type': 'file',
                    'path': relative_file_path
                })
            project_tree.append(node)
        return project_tree

    def get(self, request):
        project = Project.objects.first()
        project_path = project.project_path
        context = {'project': project, 'project_tree': self.get_project_tree(project_path)}
        return render(request, self.template_name, context)

    def post(self, request):
        action_map = {
            'delete': self.delete,
            'save_file': self.save_file,
            'rename_file': self.save_file,
            'create_dir': self.create_folder,
            'create_file': self.create_file,
            'open_file': self.open_file,
            'prompt': self.prompt
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)

    def prompt(self, request):
        project = Project.objects.first()
        project_name = project.project_name
        project_path = project.project_path
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

            return JsonResponse({'response': response.output.decode()},
                                status=response.exit_code if 100 <= response.exit_code <= 599 else 500)

        except Exception as e:
            return JsonResponse({'response': str(e)}, status=500)

    def open_file(self, request):
        project = Project.objects.first()
        project_path = project.project_path
        file_name = request.POST.get('open_file')
        file_path = os.path.join(project_path, file_name)

        # Check if the file exists
        if os.path.exists(file_path):
            # Read the file content
            with open(file_path, 'r+') as f:
                file_content = f.read()

            context = {
                'project': project,
                'file_name': file_name,
                'file_content': file_content,
                'project_tree': self.get_project_tree(project_path)
            }
            return render(request, self.template_name, context)
        else:
            # Handle case where file doesn't exist
            return HttpResponse("File not found", status=404)

    @staticmethod
    def create_folder(request):
        return HttpResponseRedirect(reverse('project'))

    @staticmethod
    def create_file(request):
        return HttpResponseRedirect(reverse('project'))

    @staticmethod
    def delete(request):
        return HttpResponseRedirect(reverse('project'))


    def save_file(self, request):
        project = Project.objects.first()
        project_path = project.project_path
        file_name = request.POST.get('save_file')
        selected_theme = request.POST.get('selected_theme')
        selected_syntax = request.POST.get('selected_syntax')
        file_content = request.POST.get('file_contents')
        file_path = os.path.join(project_path, file_name)

        # Check if the file exists
        if os.path.exists(file_path):
            # Write the file content
            with open(file_path, 'w') as f:
                f.write(file_content)

            # Update selected_theme and selected_syntax in the model
            project.selected_theme = selected_theme
            project.selected_syntax = selected_syntax
            project.save()


            context = {
                'project': project,
                'file_name': file_name,
                'file_content': file_content,
                'project_tree': self.get_project_tree(project_path)
            }
            return render(request, self.template_name, context)
        else:
            # Handle case where file doesn't exist
            return HttpResponse("File not found", status=404)
