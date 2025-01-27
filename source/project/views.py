import os
import shutil
import markdown

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse)
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.views.generic import TemplateView

from .models import Project, Task
from chat.models import ChatRoom, Message
from profile.views import add_activity_to_log
from home.models import HomePage
from user.models import CustomUser, ActivityLog
from .utils import ProjectContainerManager, GitHubUtils


def get_project_tree(project_path):
    """
    Generates a hierarchical representation of a project's directory structure,
    excluding hidden files and folders (those starting with a dot).
    """
    project_tree = []
    root_dir = os.path.basename(project_path)
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        relative_path = os.path.relpath(root, project_path)
        if relative_path == '.':
            relative_path = ''

        node = {
            'name': root_dir if relative_path == '' else os.path.join(root_dir, relative_path),
            'type': 'directory',
            'children': []
        }

        for file in files:
            if not file.startswith('.'):
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
    Update the task details for the specified project and notify users.
    """
    task = get_object_or_404(Task, id=request.POST.get('task_id'), project=project)

    # Update task details
    task.title = request.POST.get('task_title')
    task.description = request.POST.get('task_description')
    task.status = request.POST.get('task_status')
    task.save()

    add_activity_to_log(user=task.assigned_to, activity_type='task_updated', sender=request.user, task=task, project=project, message='')

    return redirect(request.META.get('HTTP_REFERER', '/'))


class ProjectView(TemplateView):
    template_name = 'project.html'

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the project view.
        """
        project_name = kwargs.get('project_name')
        current_project = Project.objects.filter(
            project_name=project_name).first() if project_name else Project.objects.order_by('-modified_at').first()

        if not current_project:
            return redirect('profile')

        project_tree = get_project_tree(current_project.project_path)
        readme_content = "<p>No README file available.</p>"
        readme_path = os.path.join(current_project.project_path, "README.md")

        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as readme_file:
                readme_content = markdown.markdown(readme_file.read())

        username = self.kwargs.get("username")
        if username:
            user_profile = get_object_or_404(CustomUser, username=username)
        else:
            user_profile = request.user

        if isinstance(request.user, AnonymousUser):
            following_users = []
            followers_users = []
            chat_rooms = []
            enabled_notifications = None
        else:
            following_users = request.user.following.all()
            followers_users = request.user.followers.all()
            chat_rooms = ChatRoom.objects.filter(participants=request.user)
            enabled_notifications = ActivityLog.objects.filter(user=request.user, notification_enabled=True)

        context = {
            'home': HomePage.objects.first(),
            'current_project': current_project,
            'project_tree': project_tree,
            'readme_content': readme_content,
            'tasks': current_project.tasks.all(),
            'recent_chats': chat_rooms,
            'enabled_notifications': enabled_notifications,
            'all_users': list(set(following_users) | set(followers_users)),
            'all_messages': Message.objects.filter(room__in=chat_rooms).order_by('timestamp'),
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for various project actions.
        """
        project_name = kwargs.get('project_name')
        project = Project.objects.filter(project_name=project_name).first()

        if not project:
            return HttpResponse("Project not found", status=404)

        action_map = {
            'add_collaborator': self.add_collaborator,
            'edit_project_details': self.edit_project_details,
            'delete_project': self.delete_project,
            'download_project': self.download_project,
            'remove_collaborator': self.remove_collaborator,
            'toggle_like': self.toggle_like,
            'add_task': self.add_task,
            'update_task': update_task,
        }

        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request, project)

        return HttpResponse("Invalid action", status=400)

    @staticmethod
    def toggle_like(request, project):
        """
        Toggle the like status for the given project.
        """
        liked_by_user = request.user in project.liked_by.all()
        project.liked_by.remove(request.user) if liked_by_user else project.liked_by.add(request.user)
        project.likes += 1 if not liked_by_user else -1
        project.save()

        return redirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def add_task(request, project):
        """
        Handle assigning tasks for a project.
        """
        assigned_to = get_object_or_404(get_user_model(), id=request.POST['assigned_to'])
        Task.objects.create(
            project=project,
            assigned_to=assigned_to,
            assigned_by=request.user,
            title=request.POST['title'],
            description=request.POST.get('description', ''),
            status='not_started'
        )

        return redirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def add_collaborator(request, project):
        """
        Handle adding a collaborator to a project.
        """
        collaborator_username = request.POST.get('username')
        try:
            collaborator = get_user_model().objects.get(username=collaborator_username)
        except get_user_model().DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)

        project.collaborators.add(collaborator)

        add_activity_to_log(user=collaborator, activity_type='collaborator_added', sender=request.user, task=None,
                            project=project, message='')
        add_activity_to_log(user=request.user, activity_type='project_updated', sender=None, task=None,
                            project=project, message=f"Added collaborator: {collaborator.username}")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def remove_collaborator(request, project):
        """
        Handle removing a collaborator from a project.
        """
        collaborator_id = request.POST.get('collaborator_id')
        try:
            collaborator = get_user_model().objects.get(id=collaborator_id)
        except get_user_model().DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)

        if collaborator in project.collaborators.all():
            project.collaborators.remove(collaborator)
            add_activity_to_log(user=collaborator, activity_type='collaborator_removed', sender=request.user, task=None,
                                project=project, message='')
            add_activity_to_log(user=request.user, activity_type='project_updated', sender=None, task=None,
                                project=project, message=f"Removed collaborator: {collaborator.username}")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def edit_project_details(request, project):
        """
        Handle updating project name, description, and visibility.
        """
        new_name, new_description = request.POST.get('name'), request.POST.get('description')
        is_public = 'is_public' in request.POST

        try:
            if project.project_name != new_name:
                os.rename(project.project_path, os.path.join(request.user.project_dir, new_name))
                project.project_path = os.path.join(request.user.project_dir, new_name)

            project.project_name, project.project_description, project.is_public = new_name, new_description, is_public
            project.save()

            add_activity_to_log(user=request.user, activity_type='project_updated', sender=None, task=None,
                                project=project, message='')

            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        except Project.DoesNotExist:
            messages.warning(request, "Project not found")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        except Exception as e:
            messages.warning(request, f"Error updating project: {e}")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    @staticmethod
    def delete_project(request, project):
        """
        Delete a project, its associated files, and its Docker container.
        """
        try:
            container_manager = ProjectContainerManager(project, request.user)
            container_manager.delete_container()
            shutil.rmtree(project.project_path)

            add_activity_to_log(user=request.user, activity_type='project_deleted', sender=None, task=None,
                                project=project, message='')
            project.delete()

        except Project.DoesNotExist:
            messages.warning(request, "Project not found")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        except Exception as e:
            messages.warning(request, f"Error deleting project: {e}")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        return redirect('profile', username=request.user.username)

    @staticmethod
    def download_project(request, project):
        """
        Create and return a zip file of the project's directory for download.
        """
        project_name = project.project_name
        project_path = project.project_path
        zip_file_path = os.path.join("/tmp", f"{os.path.basename(project_path)}.zip")

        try:
            shutil.make_archive(zip_file_path[:-4], 'zip', project_path)

            with open(zip_file_path, 'rb') as zip_file:
                response = FileResponse(zip_file, as_attachment=True)
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(project_path)}.zip"'
        except Exception:
            messages.warning(request, "Unable to Download project at this time!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        finally:
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)

        add_activity_to_log(user=request.user, activity_type='project_updated', sender=None, task=None,
                            project=project, message=f"Downloaded the project: {project_name}")

        return response


class IdeView(LoginRequiredMixin, TemplateView):
    template_name = 'ide.html'
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the IDE view.
        """
        project_name = kwargs.get('project_name')
        project = Project.objects.filter(
            project_name=project_name).first() if project_name else Project.objects.order_by('-modified_at').first()
        if not project:
            return HttpResponse("Project not found", status=404)

        readme_path, readme_content = self.handle_readme(project)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'project_tree': get_project_tree(project.project_path)})

        return render(request, self.template_name, self.get_context(request, project, readme_path, readme_content, file_name='README.md'))

    @staticmethod
    def get_context(request, project, file_path, file_content, file_name):
        """
        method to get all template context and return it.
        """""

        context = {
            'is_read_only': not (request.user in project.collaborators.all() or request.user == project.user),
            'home': HomePage.objects.first(),
            'current_project': project,
            'project_tree': get_project_tree(project.project_path),
            'file_name': file_name,
            'file_path': file_path,
            'file_content': file_content,
            'tasks': project.tasks.all(),
            'is_git_repo': bool(project.repository),
            'uncommitted_files': GitHubUtils.get_uncommitted_files(request, project) if project.repository else [],
            'branch': GitHubUtils.get_current_branch(request, project),
        }
        return context

    @staticmethod
    def handle_readme(project):
        """Ensure the README.md file exists and return its path and content."""
        readme_path = os.path.join(project.project_path, 'README.md')

        if not os.path.exists(readme_path):
            with open(readme_path, 'w', encoding='utf-8') as file:
                file.write(f"# Welcome to your {project.project_name}!\n\nThis is the README.md file for your project.\n\n{project.project_description or 'No description provided.'}")

        try:
            with open(readme_path, 'r', encoding='utf-8') as file:
                readme_content = file.read()
        except Exception as e:
            raise IOError(f"Error reading README.md: {e}")

        return readme_path, readme_content

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for various project actions.
        """
        project_name = kwargs.get('project_name')
        project = Project.objects.filter(project_name=project_name).first()

        if not project:
            return HttpResponse("Project not found", status=404)

        action_map = {
            'delete': self.delete,
            'save_file': self.save_file,
            'rename_file': self.save_file,
            'open_file': self.open_file,
            'update_ide_settings': self.update_ide_settings,
            'update_task': update_task,
            'create_git_repo': GitHubUtils.create_git_repo,
            'commit_files': GitHubUtils.commit_files,
            'push_all_commits': GitHubUtils.push_all_commits,
            'commit_push_files': GitHubUtils.commit_files,
            'pull_and_update_files': GitHubUtils.pull_and_update_files,
        }

        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request, project)

        return HttpResponse("Invalid action", status=400)

    @staticmethod
    def update_ide_settings(request, project):
        """
        Update the theme and syntax for a project.
        """
        settings = request.user.idesettings
        settings.selected_theme = request.POST.get('theme')
        settings.selected_syntax = request.POST.get('syntax')
        settings.show_line_numbers = 'on' in request.POST.getlist("show_line_numbers")
        settings.auto_close_brackets = 'on' in request.POST.getlist("auto_close_brackets")
        settings.match_brackets = 'on' in request.POST.getlist("match_brackets")
        settings.highlight_current_line = 'on' in request.POST.getlist("highlight_current_line")
        settings.line_wrapping = 'on' in request.POST.getlist("line_wrapping")
        settings.indent_with_tabs = 'on' in request.POST.getlist("indent_with_tabs")
        settings.linting = 'on' in request.POST.getlist("linting")
        settings.tab_size = request.POST.get("tab_size")
        settings.font_size = request.POST.get("font_size")
        settings.last_modified_at = now()
        settings.save()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def open_file(self, request, project):
        """
        Open a file within the specified project and return its content.
        """
        file_path = request.POST.get('open_file')
        if not file_path or not os.path.exists(file_path):
            messages.warning(request, "File Not Found!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
        except Exception:
            messages.warning(request, "Error Reading File!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        return render(request, self.template_name, self.get_context(request, project, file_path, file_content, file_name=os.path.basename(file_path)))

    @staticmethod
    def delete(request, project):
        """
        Delete a specified file from the project.
        """
        file_path = request.POST.get('file_path')

        try:
            os.remove(file_path)
            action = f"Deleted file {os.path.basename(file_path)}"
        except OSError as e:
            action = f"Failed to delete file {file_path}: {e}"
            messages.warning(request, f"Failed to delete file {file_path}: {e}")

        add_activity_to_log(user=request.user, activity_type='project_updated', sender=None, task=None,
                            project=project, message=action)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def save_file(self, request, project):
        """
        Save or rename an existing file in the project and update project settings.
        """

        file_name = request.POST.get('file_name')
        file_content = request.POST.get('file_contents', '')
        file_path = request.POST.get('file_path')
        new_file_name = request.POST.get('new_file_name')

        if new_file_name:
            if not file_path:
                messages.warning(request, "File path is required to rename a file.")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

            new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
            try:
                os.rename(file_path, new_file_path)
                file_name = new_file_name
                file_path = new_file_path
                action = f"Renamed file to {new_file_name}"
            except Exception:
                messages.warning(request, "Error renaming file.")
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        elif file_path:
            action = f"Saved changes to file {file_name}"
        else:
            messages.warning(request, "File path is required to save changes.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        try:
            normalized_content = file_content.replace('\r\n', '\n').replace('\r', '\n')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(normalized_content)
        except Exception:
            messages.warning(request, "Error saving file.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        add_activity_to_log(user=request.user, activity_type='project_updated', sender=None, task=None,
                            project=project, message=action)

        return render(request, self.template_name, self.get_context(request, project, file_path, file_content, file_name))
