import os
import subprocess
from datetime import timedelta
from github import Github

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.utils.timezone import now
from django.views.generic import TemplateView
from django.core.files.storage import FileSystemStorage

from chat.models import ChatRoom, Message
from project.models import Project
from user.models import CustomUser, Notification


def add_activity_to_log(user, project_name, action):
    """
    Add a new activity entry to the user's activity log.
    """
    new_activity = {
        'project_name': project_name,
        'date_time': now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': action,
    }

    # Append the new activity to the activity log
    if isinstance(user.activity_log, list):
        user.activity_log.append(new_activity)
    else:
        user.activity_log = [new_activity]

    # Save the updated activity log
    user.save()


def user_activity(user_projects, user_profile):
    """
    Retrieve the 5 most recent activities and the activity data for the past year
    based on the activity_log field of the user.
    """
    recent_activity = user_profile.activity_log

    # Generate activity data for the past year
    start_date = now() - timedelta(days=365)
    end_date = now()

    # Create a dictionary to count activities per day
    activity_data = {}
    for entry in user_profile.activity_log:
        entry_date = now().strptime(entry['date_time'], '%Y-%m-%d %H:%M:%S').date()
        if start_date.date() <= entry_date <= end_date.date():
            activity_data[entry_date] = activity_data.get(entry_date, 0) + 1

    # Generate a list of activity data for each day in the past year
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

        # Get the user profile
        if username:
            user_profile = get_object_or_404(CustomUser, username=username)
            owned_projects = Project.objects.filter(user=user_profile)
            collaborating_projects = user_profile.collaborating_projects.all()
        else:
            user_profile = request.user
            owned_projects = Project.objects.filter(user=request.user)
            collaborating_projects = request.user.collaborating_projects.all()

        user_projects = owned_projects | collaborating_projects

        # Manage anonymous and logged-in users
        if isinstance(request.user, AnonymousUser):
            user_projects = user_projects.filter(is_public=True)
            is_following = False
            following_users = []
            followers_users = []
            chat_rooms = []
            unread_notifications = None
        else:
            if user_profile != request.user:
                user_projects = user_projects.filter(
                    models.Q(is_public=True) | models.Q(collaborators=request.user)
                )
            is_following = request.user.is_following(user_profile)
            following_users = request.user.following.all()
            followers_users = request.user.followers.all()
            chat_rooms = ChatRoom.objects.filter(participants=request.user)
            unread_notifications = Notification.objects.filter(user=request.user, is_read=False)

        # Ensure distinct and ordered user projects
        user_projects = user_projects.distinct().order_by('-modified_at')

        # Get user activity information
        activity_days, recent_activity = user_activity(user_projects, user_profile)

        # Fetch GitHub repositories if it's the user's own profile
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
            'unread_notifications': unread_notifications,
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
            'edit_profile': self.edit_profile,
            'edit_bio': self.edit_bio,
            'update_password': self.update_password,
            'follow_unfollow': self.follow_unfollow,
            'clone_repo': self.clone_repo,
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)
        return HttpResponse("Invalid action", status=400)

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
        Create a new project and redirect to the IDE view.
        """
        project_name = request.POST.get('project_name')
        project_description = request.POST.get('project_description')

        try:
            project_path = os.path.join(request.user.project_dir, project_name)
            os.makedirs(project_path, exist_ok=True)

            project = Project(
                project_name=project_name,
                project_description=project_description,
                user=request.user,
                project_path=project_path,
            )
            project.save()

            readme_path = os.path.join(project.project_path, "README.md")
            with open(readme_path, "w") as readme_file:
                readme_content = f"# {project_name}\n\n{project_description or 'No description provided.'}"
                readme_file.write(readme_content)

        except Exception as e:
            return HttpResponse(f"Error creating project: {e}", status=500)

        action = 'Created Project'
        add_activity_to_log(request.user, project.project_name, action)

        return redirect('project', username=request.user, project_id=project.id)

    @staticmethod
    def edit_profile(request):
        """
        Handle the profile update logic (including picture, username, and email).
        """
        user = request.user
        profile_picture = request.FILES.get('profile_picture', None)
        if profile_picture:
            fs = FileSystemStorage()
            filename = fs.save(profile_picture.name, profile_picture)
            user.profile_picture = fs.url(filename)

        username = request.POST.get('username')
        email = request.POST.get('email')

        if username:
            user.username = username
        if email:
            user.email = email

        user.save()

        return redirect('profile', username=request.user)

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
    def update_password(request):
        """
        Handle the password update logic.
        """
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not check_password(current_password, user.password):
            messages.error(request, "The current password is incorrect.")
            return redirect('profile', username=request.user)

        if new_password != confirm_new_password:
            messages.error(request, "The new passwords do not match.")
            return redirect('profile', username=request.user)

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(request, "Your password has been updated successfully.")
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
            Notification.objects.create(
                user=target_user,
                sender=user,
                notification_type='new_follower',
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
