import os
import shutil
import markdown
from github import Github
from social_django.models import UserSocialAuth

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse, FileResponse)
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from django.views.generic import TemplateView

from chat.models import ChatRoom, Message
from profile.views import add_activity_to_log
from user.models import ActivityLog
from .models import Project, Task
from .utils import ProjectContainerManager


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
            # Skip hidden files
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

    add_activity_to_log(user=task.assigned_to, activity_type='task', sender=request.user, task=task, project=project, message=f"{request.user.username} updated task {task.title}")

    return redirect(request.META.get('HTTP_REFERER', '/'))


class ProjectView(TemplateView):
    template_name = 'project.html'

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the project view.
        """
        project_id = kwargs.get('project_id')
        current_project = Project.objects.filter(id=project_id).first() if project_id else Project.objects.order_by(
            '-modified_at').first()

        if not current_project:
            return redirect('personal_profile')

        project_tree = get_project_tree(current_project.project_path)
        readme_content = "<p>No README file available.</p>"
        readme_path = os.path.join(current_project.project_path, "README.md")

        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as readme_file:
                readme_content = markdown.markdown(readme_file.read())

        context = {
            'current_project': current_project,
            'project_tree': project_tree,
            'readme_content': readme_content,
            'tasks': current_project.tasks.all(),
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for various project actions.
        """
        project_id = kwargs.get('project_id')
        project = Project.objects.filter(id=project_id).first()

        if not project:
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

        add_activity_to_log(user=collaborator, activity_type='project', sender=request.user, task=None,
                            project=project,
                            message=f"{request.user.username} added {collaborator.username} to project {project.project_name}")

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
            add_activity_to_log(user=collaborator, activity_type='project', sender=request.user, task=None,
                                project=project, message=f"{request.user.username} removed {collaborator.username} from project {project.project_name}")

            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        return JsonResponse({'error': 'User is not a collaborator'}, status=400)

    @staticmethod
    def edit_project_details(request, project):
        """
        Handle updating project name, description, and visibility.
        """
        new_name, new_description = request.POST.get('name'), request.POST.get('description')
        is_public = 'is_public' in request.POST

        if not new_name or not new_description:
            return HttpResponseBadRequest("Name and description cannot be empty")

        try:
            if project.project_name != new_name:
                os.rename(project.project_path, os.path.join(request.user.project_dir, new_name))
                project.project_path = os.path.join(request.user.project_dir, new_name)

            project.project_name, project.project_description, project.is_public = new_name, new_description, is_public
            project.save()

            add_activity_to_log(user=request.user, activity_type='project', sender=None, task=None,
                                project=project, message=f"{request.user.username} updated project: {project.project_name}'s details")

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
            container_manager = ProjectContainerManager(project, request.user)
            container_manager.delete_container()
            shutil.rmtree(project.project_path)

            add_activity_to_log(user=request.user, activity_type='project', sender=None, task=None,
                                project=project, message=f"{request.user.username} Deleted Project {project.project_name}")
            project.delete()

        except Project.DoesNotExist:
            return HttpResponse("Project not found", status=404)
        except Exception as e:
            return HttpResponse(f"Error deleting project: {e}", status=500)

        return redirect('profile', username=request.user.username)


class IdeView(LoginRequiredMixin, TemplateView):
    template_name = 'ide.html'
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the IDE view.
        """
        project_id = kwargs.get('project_id')
        current_project = Project.objects.filter(id=project_id).first() if project_id else Project.objects.order_by(
            '-modified_at').first()

        if not current_project:
            return redirect('personal_profile')

        readme_path = os.path.join(current_project.project_path, 'README.md')
        if not os.path.exists(readme_path):
            with open(readme_path, 'w', encoding='utf-8') as file:
                file.write("# Welcome to your project\n\nThis is the README.md file for your project.")

        try:
            with open(readme_path, 'r', encoding='utf-8') as file:
                readme_content = file.read()
        except Exception as e:
            return HttpResponse(f"Error reading README.md: {e}", status=500)

        project_tree = get_project_tree(current_project.project_path)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'project_tree': project_tree})

        following_users = request.user.following.all()
        followers_users = request.user.followers.all()
        chat_rooms = ChatRoom.objects.filter(participants=request.user)

        # Check if the project has a valid repository
        is_git_repo = current_project.repository if current_project.repository else None

        # Initialize git_commits and uncommitted_files to empty lists
        git_commits = []
        uncommitted_files = []

        if is_git_repo:
            try:
                github_account = request.user.social_auth.get(provider='github')
                token = github_account.access_token  # Get the access token from the GitHub account

                # Use the token to authenticate with the GitHub API
                g = Github(token)

                # Access the repository using the repo name (replace 'owner' with the GitHub repository owner)
                repo = g.get_repo(current_project.repository)

                # Fetch commits from GitHub repository
                commits = repo.get_commits()

                git_commits = [
                    {
                        'message': commit.commit.message,
                        'date': commit.committer.date.strftime('%Y-%m-%d %H:%M:%S'),
                        'author': commit.committer.name,
                        'id': commit.sha,
                        'files_changed': len(commit.files)
                    } for commit in commits
                ]

                # Fetch files from the repository to compare with the local project files
                contents = repo.get_contents("")  # Get all files in the root of the repository
                repo_files = {content.path: content.sha for content in contents}

                # Now, compare the local project files with the ones from the repository
                local_files = []  # Assume this contains the list of local files (either from database or file system)

                # Compare files
                for local_file in local_files:
                    if local_file not in repo_files:
                        uncommitted_files.append({
                            'file': local_file,
                            'change_type': 'Untracked'
                        })
                    else:
                        # Compare file content or modification date if needed
                        # For simplicity, we'll assume the file is uncommitted if it doesn't match
                        if local_file_sha != repo_files.get(local_file):
                            uncommitted_files.append({
                                'file': local_file,
                                'change_type': 'Modified'
                            })

            except UserSocialAuth.DoesNotExist:
                github_account = None
                git_commits = []
                uncommitted_files = []
            except Exception as e:
                # Handle any other exceptions, such as issues with accessing the repository
                git_commits = []
                uncommitted_files = []

        context = {
            'all_projects': Project.objects.all(),
            'current_project': current_project,
            'project_tree': project_tree,
            'file_name': 'README.md',
            'file_path': readme_path,
            'file_content': readme_content,
            'tasks': current_project.tasks.all(),
            'recent_chats': chat_rooms,
            'all_users': (following_users | followers_users).distinct(),
            'all_messages': Message.objects.filter(room__in=chat_rooms).order_by('timestamp'),
            'git_commits': git_commits,
            'is_git_repo': is_git_repo,
            'uncommitted_files': uncommitted_files,
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for various project actions.
        """
        project = Project.objects.filter(id=kwargs.get('project_id')).first()

        if not project:
            return HttpResponse("Project not found", status=404)

        action_map = {
            'delete': self.delete,
            'save_file': self.save_file,
            'rename_file': self.save_file,
            'open_file': self.open_file,
            'download_project': self.download_project,
            'update_theme': self.update_theme,
            'update_task': update_task,
            'commit_project': self.commit_project,
            'commit_push_project': self.commit_push_project

        }

        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request, project)

        return HttpResponse("Invalid action", status=400)

    @staticmethod
    def commit_project(request, project):
        commit_message = request.POST.get('commit_message')

        if not commit_message:
            return HttpResponse("Commit message is required", status=400)

        try:
            github_account = request.user.social_auth.get(provider='github')
            token = github_account.extra_data.get('access_token')

            g = Github(token)
            repo = g.get_repo(project.repository)

            repo.create_git_commit(
                commit_message,
                repo.get_git_tree('main'),
                [repo.get_git_ref('heads/main').object]
            )
        except Exception as e:
            return HttpResponse(f"Error committing: {str(e)}", status=500)

        return HttpResponse("Commit successful", status=200)

    @staticmethod
    def commit_push_project(request, project):
        commit_message = request.POST.get('commit_message')
        if not commit_message:
            return HttpResponse("Commit message is required", status=400)

        try:
            github_account = request.user.social_auth.get(provider='github')
            token = github_account.extra_data.get('access_token')

            g = Github(token)
            repo = g.get_repo(project.repository)

            branch = repo.get_branch('main')
            base_sha = branch.commit.sha
            new_commit = repo.create_git_commit(
                commit_message,
                repo.get_git_tree(base_sha),
                [repo.get_git_ref('heads/main').object]
            )

            repo.get_git_ref('heads/main').edit(new_commit.sha)
        except Exception as e:
            return HttpResponse(f"Error committing and pushing: {str(e)}", status=500)

        return HttpResponse("Commit and push successful", status=200)

    @staticmethod
    def update_theme(request, project):
        """
        Update the theme and syntax for a project.
        """
        project.selected_theme = request.POST.get('selected_theme', 'default_theme')
        project.selected_syntax = request.POST.get('selected_syntax', 'default_syntax')
        project.last_modified_at = now()
        project.save()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def open_file(self, request, project):
        """
        Open a file within the specified project and return its content.
        """
        file_path = request.POST.get('open_file')
        if not file_path or not os.path.exists(file_path):
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
        file_path = request.POST.get('file_path')

        if not file_path or not os.path.exists(file_path):
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        try:
            os.remove(file_path)
            action = f"Deleted file {os.path.basename(file_path)}"
        except OSError as e:
            action = f"Failed to delete file {file_path}: {e}"

        add_activity_to_log(user=request.user, activity_type='update_project', sender=None, task=None,
                            project=project, message=action)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def save_file(self, request, project):
        """
        Save, rename, or create a new file in the project and update project settings.
        """
        user = request.user
        project_name = project.project_name

        file_name = request.POST.get('file_name')
        file_content = request.POST.get('file_contents', '')
        file_path = request.POST.get('file_path')
        new_file_name = request.POST.get('new_file_name')

        project_path = project.project_path
        action = ''

        if new_file_name:
            file_path = file_path or os.path.join(project_path, new_file_name)
            os.rename(file_path, os.path.join(os.path.dirname(file_path), new_file_name)) if file_path else None
            file_name = new_file_name
            action = f"Renamed file {file_name} to {new_file_name}" if file_path else f"Created a new file {new_file_name}"
        elif file_path:
            action = f"Saved changes to file {file_name}"
        else:
            file_path = os.path.join(project_path, file_name or 'new_file.txt')
            file_name = file_name or 'new_file.txt'
            action = f"Created a new file {file_name}"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
        except Exception as e:
            return HttpResponse(f"Error saving file: {e}", status=500)

        add_activity_to_log(user=request.user, activity_type='update_project', sender=None, task=None,
                            project=project, message=action)

        context = {
            'all_projects': Project.objects.all(),
            'current_project': project,
            'file_name': file_name,
            'file_path': file_path,
            'file_content': file_content,
            'project_tree': get_project_tree(project_path),
        }

        return render(request, self.template_name, context)

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
        except Exception as e:
            return HttpResponse(f"Error creating zip file: {e}", status=500)
        finally:
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)

        add_activity_to_log(user=request.user, activity_type='update_project', sender=None, task=None,
                            project=project, message=f"Downloaded the project {project_name}")

        return response
