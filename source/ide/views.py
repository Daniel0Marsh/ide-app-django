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
        project_path = current_project.project_path
        context = {
            'all_projects': all_projects,
            'current_project': current_project,
            'project_tree': self.get_project_tree(project_path)
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action_map = {
            'delete': self.delete,
            'save_file': self.save_file,
            'rename_file': self.save_file,
            'open_file': self.open_file,
            'prompt': self.prompt,
            'open_project': self.open_project
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

            return JsonResponse({'response': response.output.decode()},
                                status=response.exit_code if 100 <= response.exit_code <= 599 else 500)

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

        # Check if the file exists
        if not os.path.exists(file_path):
            if new_file_name:
                file_name = new_file_name
            else:
                file_name = "new_file.txt"

        if selected_syntax and selected_theme:
            # Update selected_theme and selected_syntax in the model
            current_project.selected_theme = selected_theme
            current_project.selected_syntax = selected_syntax
            current_project.save()

        with open(os.path.join(project_path, file_name), 'w') as f:
            f.write(file_content)

        context = {
            'all_projects': all_projects,
            'current_project': current_project,
            'file_name': file_name,
            'file_path': file_path,
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
