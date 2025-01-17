import zipfile
import os
import subprocess
from datetime import timedelta
from github import Github

from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.timezone import now
from django.views.generic import TemplateView

from chat.models import ChatRoom, Message
from project.models import Project
from user.models import CustomUser, Notification


def create_notification(user, notification_type, sender=None, task=None, project=None, message=None):
    """
    Create a notification for a user if the notification type is enabled for the user.
    """
    notification = Notification.objects.filter(user=user, notification_type=notification_type).first()

    if notification and notification.notification_enabled:
        new_notification = Notification(
            user=user,
            sender=sender,
            notification_type=notification_type,
            task=task,
            project=project,
            message=message,
        )
        new_notification.save()
        return new_notification
    else:
        return None


def add_activity_to_log(user, project_name, action):
    """
    Add a new activity entry to the user's activity log.
    """
    new_activity = {
        'project_name': project_name,
        'date_time': now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': action,
    }

    if isinstance(user.activity_log, list):
        user.activity_log.append(new_activity)
    else:
        user.activity_log = [new_activity]

    user.save()


def user_activity(user_projects, user_profile):
    """
    Retrieve the 5 most recent activities and the activity data for the past year
    based on the activity_log field of the user.
    """
    recent_activity = user_profile.activity_log

    start_date = now() - timedelta(days=365)
    end_date = now()

    activity_data = {}
    for entry in user_profile.activity_log:
        entry_date = now().strptime(entry['date_time'], '%Y-%m-%d %H:%M:%S').date()
        if start_date.date() <= entry_date <= end_date.date():
            activity_data[entry_date] = activity_data.get(entry_date, 0) + 1

    activity_days = [
        {'date': current_date, 'count': activity_data.get(current_date.date(), 0)}
        for current_date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1))
    ]

    return activity_days, recent_activity


class ProfileView(TemplateView):
    template_name = 'profile.html'

    def get(self, request, *args, **kwargs):
        """
        Render the profile page, showing the logged-in user's profile or another user's profile.
        Also, fetch the user's GitHub repositories with a clone button.
        """
        username = self.kwargs.get("username")

        if username:
            user_profile = get_object_or_404(CustomUser, username=username)
        else:
            user_profile = request.user

        owned_projects = Project.objects.filter(user=user_profile)
        collaborating_projects = user_profile.collaborating_projects.all()

        user_projects = owned_projects | collaborating_projects

        if isinstance(request.user, AnonymousUser):
            user_projects = user_projects.filter(is_public=True)
            is_following = False
            following_users = []
            followers_users = []
            chat_rooms = []
            enabled_notifications = None
        else:
            if user_profile != request.user:
                user_projects = user_projects.filter(
                    models.Q(is_public=True) | models.Q(collaborators=request.user)
                )
            is_following = request.user.is_following(user_profile)
            following_users = request.user.following.all()
            followers_users = request.user.followers.all()
            chat_rooms = ChatRoom.objects.filter(participants=request.user)
            enabled_notifications = Notification.objects.filter(user=request.user, notification_enabled=True)

        user_projects = user_projects.distinct().order_by('-modified_at')

        activity_days, recent_activity = user_activity(user_projects, user_profile)

        github_repos = []
        if user_profile == request.user and not isinstance(request.user, AnonymousUser):
            try:
                access_token = request.user.social_auth.get(provider='github').extra_data['access_token']
                github = Github(access_token)
                github_repos = github.get_user().get_repos()
            except Exception as e:
                print(f"Error fetching GitHub repos: {e}")

        context = {
            'user_profile': user_profile,
            'user_projects': user_projects,
            'activity_days': activity_days,
            'recent_activity': recent_activity,
            'is_own_profile': user_profile == request.user,
            'is_following': is_following,
            'recent_chats': chat_rooms,
            'all_users': list(set(following_users) | set(followers_users)),
            'all_messages': Message.objects.filter(room__in=chat_rooms).order_by('timestamp'),
            'enabled_notifications': enabled_notifications,
            'github_repos': github_repos,
        }

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Handle actions such as opening, deleting, or creating a project.
        """
        action_map = {
            'open_project': self.open_project,
            'create_project': self.create_project,
            'clone_repo': self.clone_repo,
            'edit_bio': self.edit_bio,
            'follow_unfollow': self.follow_unfollow,
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)
        return HttpResponse("Invalid action", status=400)

    @staticmethod
    def open_project(request):
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

        return redirect('ide', username=request.user.username, project_id=project.id)

    @staticmethod
    def create_project(request):
        """
        Create a new project, handle file upload (.zip), and redirect to the IDE view.
        """
        project_name = request.POST.get('project_name')
        project_description = request.POST.get('project_description')
        project_folder = request.FILES.get('project_folder')
        project_path = os.path.join(request.user.project_dir, project_name)

        os.makedirs(project_path, exist_ok=True)

        if project_folder:
            extracted_path = os.path.join(project_path, 'another')
            os.makedirs(extracted_path, exist_ok=True)
            with zipfile.ZipFile(project_folder, 'r') as zip_ref:
                for file_info in zip_ref.namelist():
                    target_path = os.path.join(extracted_path, file_info)
                    if file_info.endswith(os.sep):
                        os.makedirs(target_path, exist_ok=True)
                    else:
                        with zip_ref.open(file_info) as src, open(target_path, 'wb') as dest:
                            dest.write(src.read())

        project = Project.objects.create(
            project_name=project_name,
            project_description=project_description,
            user=request.user,
            project_path=project_path,
        )

        # Create README
        with open(os.path.join(project_path, "README.md"), "w") as readme_file:
            readme_file.write(f"# {project_name}\n\n{project_description or 'No description provided.'}")

        add_activity_to_log(request.user, project.project_name, 'Created Project')

        return redirect('project', username=request.user.username, project_id=project.id)

    @staticmethod
    def clone_repo(request):
        """
        Create a new project using the repo name and clone the repo into the user's project directory.
        """
        repo_url = request.POST.get('repo_url')
        repo_name = repo_url.split('/')[-1]

        user_project_dir = request.user.project_dir

        project_dir = os.path.join(user_project_dir, repo_name)
        os.makedirs(project_dir, exist_ok=True)

        project = Project.objects.create(
            user=request.user,
            project_name=repo_name,
            project_path=project_dir,
            project_description=f"Cloned from {repo_url}",
        )

        try:
            subprocess.run(['git', 'clone', repo_url, project_dir], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error while cloning repository: {e}")
            return HttpResponse("Error cloning repository", status=500)

        action = 'Cloned Project'
        add_activity_to_log(request.user, project.project_name, action)

        return redirect('ide', username=request.user.username, project_id=project.id)

    @staticmethod
    def edit_bio(request):
        """
        Handle updating user profile bio.
        """
        user = request.user
        bio = request.POST.get('bio')

        if bio:
            user.bio = bio

        user.save()

        return redirect('profile', username=request.user)

    @staticmethod
    def follow_unfollow(request):
        """
        Handle follow/unfollow action.
        """
        user = request.user
        target_username = request.POST.get('target_user')
        target_user = get_object_or_404(CustomUser, username=target_username)

        if user == target_user:
            return redirect('profile', username=target_username)

        if user.is_following(target_user):
            user.unfollow(target_user)
        else:
            user.follow(target_user)

            create_notification(
                user=target_user,
                notification_type='new_follower',
                sender=user,
                task=None,
                project=None,
                message=f"{user.username} is now following you."
            )

        return redirect('profile', username=target_username)


class SearchView(TemplateView):
    template_name = "search_results.html"

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for searching users and projects.
        """
        query = request.GET.get('query', '').strip()
        user_results = []
        project_results = []

        if query:
            user_results = CustomUser.objects.filter(
                Q(username__icontains=query) | Q(email__icontains=query)
            )
            project_results = Project.objects.filter(
                Q(project_name__icontains=query) | Q(project_description__icontains=query)
            ).filter(is_public=True)

        context = {
            'query': query,
            'user_results': user_results,
            'project_results': project_results,
        }

        return self.render_to_response(context)
