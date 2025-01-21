import zipfile
import os
import subprocess
from datetime import timedelta
from github import Github

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.timezone import now
from django.views.generic import TemplateView

from chat.models import ChatRoom, Message
from project.models import Project
from user.models import CustomUser, ActivityLog
from home.models import HomePage


def add_activity_to_log(user, activity_type, sender=None, task=None, project=None, message=None):
    """
    Create a notification for a user if the notification type is enabled for the user.
    """

    new_activity = ActivityLog(
        user=user,
        sender=sender,
        activity_type=activity_type,
        task=task,
        project=project,
        message=message,
    )
    new_activity.save()
    return new_activity


def user_activity(user_profile, selected_year=None):
    """
    Retrieve the 5 most recent activities and the activity data for the selected year
    or the current year by default.
    """
    current_year = now().year
    selected_year = selected_year or current_year
    start_date = now().date().replace(year=int(selected_year), month=1, day=1)
    end_date = now().date().replace(year=int(selected_year), month=12, day=31)
    recent_activities = ActivityLog.objects.filter(user=user_profile).order_by('-created_at')[:5]

    activity_logs = ActivityLog.objects.filter(
        user=user_profile,
        created_at__gte=start_date,
        created_at__lte=end_date
    )

    activity_grid = [[0] * 52 for _ in range(7)]

    for log in activity_logs:
        log_date = log.created_at.date()
        day_of_week = log_date.weekday()
        week_number = min((log_date - start_date).days // 7, 51)
        activity_grid[day_of_week][week_number] += 1

    activity_days = [
        {
            'day_of_week': day,
            'week': week,
            'count': activity_grid[day][week],
            'date': (start_date + timedelta(days=week * 7 + day)).strftime("%B %d, %Y")
        }
        for day in range(7) for week in range(52)
    ]

    years = list(range(current_year - 4, current_year + 1))

    return activity_days, recent_activities, years


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
            enabled_notifications = ActivityLog.objects.filter(user=request.user, notification_enabled=True)

        user_projects = user_projects.distinct().order_by('-modified_at')

        activity_days, recent_activity, years = user_activity(user_profile)

        github_repos = []
        if not isinstance(request.user, AnonymousUser):
            try:
                if user_profile == request.user:
                    access_token = request.user.social_auth.get(provider='github').extra_data['access_token']
                else:
                    access_token = user_profile.social_auth.get(provider='github').extra_data['access_token']

                github = Github(access_token)
                github_repos = github.get_user().get_repos()
            except Exception:
                messages.warning(request, "Error fetching GitHub repos. Please go to settings and connect your GitHub account.")

        context = {
            'home': HomePage.objects.first(),
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
            'years': years,
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
    @csrf_exempt
    def user_activity_ajax(request, username):
        """
        method to handle changing years for activity calendar using ajax requests
        """
        user_profile = get_object_or_404(CustomUser, username=username)
        selected_year = request.GET.get('year')

        activity_days, _, _ = user_activity(user_profile, selected_year)
        return JsonResponse({
            'activity_days': activity_days,
        })

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
            readme_file.write(f"# Welcome to your {project_name}!\n\nThis is the README.md file for your project.\n\n{project_description or 'No description provided.'}")

        add_activity_to_log(request.user, activity_type='project', sender=None, task=None, project=project, message='You created a new project')

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
            repository=repo_url,
            project_description=f"Cloned from {repo_url}",
        )

        try:
            subprocess.run(['git', 'clone', repo_url, project_dir], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error while cloning repository: {e}")
            return HttpResponse("Error cloning repository", status=500)

        add_activity_to_log(request.user, activity_type='project', sender=None, task=None, project=project,
                            message='You cloned a repository')

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

            add_activity_to_log(user=target_user, activity_type='new_follower', sender=user, task=None,
                                project=None, message=None)

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
            'home': HomePage.objects.first(),
            'query': query,
            'user_results': user_results,
            'project_results': project_results,
        }

        return self.render_to_response(context)
