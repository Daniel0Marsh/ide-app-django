from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib import messages
from ide.models import Project
from ide.views import ProjectContainerManager, get_project_tree
from user.models import CustomUser
import os
import shutil


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "profile.html"
    login_url = 'login'  # Redirect to the login page if not authenticated

    def get(self, request, *args, **kwargs):
        """
        Render the profile page, which can either show the logged-in user's profile
        or another user's profile based on the 'username' parameter.
        """
        # Check if a username is passed in the URL
        username = self.kwargs.get("username")

        # If a username is provided, load the profile of that user; otherwise, load the current user's profile
        if username:
            user_profile = get_object_or_404(CustomUser, username=username)
            user_projects = Project.objects.filter(user=user_profile)
        else:
            user_profile = request.user
            user_projects = Project.objects.filter(user=request.user)

        recent_activities, days = self.user_activity(user_projects)
        is_following = request.user.is_authenticated and request.user.is_following(user_profile)

        context = {
            'user_profile': user_profile,  # Pass the user profile to the template
            'user_projects': user_projects,
            'recent_activities': recent_activities,
            'activity_days': days,
            'is_own_profile': user_profile == request.user,  # Check if it's the current user's profile,
            'is_following': is_following,
        }
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Handle actions such as opening, deleting, or creating a project.
        """
        action_map = {
            'open_project': self.open_project,
            'delete_project': self.delete_project,
            'create_project': self.create_project,
            'edit_profile': self.edit_profile,
            'edit_bio': self.edit_bio,
            'update_password': self.update_password,
            'follow_unfollow': self.follow_unfollow
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

    def edit_profile(self, request):
        """
        Handle the profile update logic (including picture, username, and email).
        """
        user = request.user
        # Check if the form has a profile picture and handle it
        profile_picture = request.FILES.get('profile_picture', None)
        if profile_picture:
            fs = FileSystemStorage()
            filename = fs.save(profile_picture.name, profile_picture)
            user.profile_picture = fs.url(filename)

        # Update the username and email
        username = request.POST.get('username')
        email = request.POST.get('email')

        if username:
            user.username = username
        if email:
            user.email = email

        user.save()

        # Redirect back to the profile or wherever needed
        return redirect('personal_profile')

    def edit_bio(self, request):
        """
        Handle updating user profile bio.
        """
        user = request.user

        # Get bio and username from the POST data
        bio = request.POST.get('bio')

        # Update the user's profile
        if bio:
            user.bio = bio

        user.save()

        # Redirect back to the profile or wherever needed
        return redirect('personal_profile')

    def update_password(self, request):
        """
        Handle the password update logic.
        """
        user = request.user

        # Get the form data
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        # Validate the current password
        if not check_password(current_password, user.password):
            messages.error(request, "The current password is incorrect.")
            return redirect('personal_profile')

        # Validate new password and confirmation
        if new_password != confirm_new_password:
            messages.error(request, "The new passwords do not match.")
            return redirect('personal_profile')

        # Update the password
        user.set_password(new_password)
        user.save()

        # Keep the user logged in after password change
        update_session_auth_hash(request, user)

        messages.success(request, "Your password has been updated successfully.")
        return redirect('personal_profile')

    def follow_unfollow(self, request):
        """
        Handle follow/unfollow action.
        """
        user = request.user
        target_username = request.POST.get('target_user')
        target_user = get_object_or_404(CustomUser, username=target_username)

        if user == target_user:
            return redirect('personal_profile')

        if user.is_following(target_user):
            user.unfollow(target_user)
        else:
            user.follow(target_user)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

