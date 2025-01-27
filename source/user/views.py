import os
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import CustomUser, SenderEmailSettings
from social_django.utils import psa
from social_django.models import UserSocialAuth
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.views.generic import TemplateView, View
from .models import ActivityLog


class SettingsView(LoginRequiredMixin, TemplateView):
    """Handle settings page where user can update their details and preferences."""
    template_name = 'settings.html'
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        """Render settings form with user details and preferences."""

        try:
            github_account = request.user.social_auth.get(provider='github')
        except UserSocialAuth.DoesNotExist:
            github_account = None

        # Calculate the current folder size
        current_folder_size = self.get_folder_size(request.user.project_dir)  # In MB

        # Get the folder size limit (assuming it's a model field for user)
        project_folder_size_limit = request.user.project_folder_size_limit

        # Calculate remaining space
        remaining_size = project_folder_size_limit - current_folder_size

        context = {
            'needs_password': bool(request.user.password),
            'github_account': github_account,
            'enabled_notifications': ActivityLog.objects.filter(user=request.user, notification_enabled=True),
            'new_follower': ActivityLog.objects.filter(user=request.user, activity_type='new_follower', notification_enabled=True).first(),
            'task': ActivityLog.objects.filter(user=request.user, activity_type='task', notification_enabled=True).first(),
            'new_message': ActivityLog.objects.filter(user=request.user, activity_type='new_message', notification_enabled=True).first(),
            'project': ActivityLog.objects.filter(user=request.user, activity_type='project', notification_enabled=True).first(),
            'current_folder_size': current_folder_size,
            'remaining_size': remaining_size,
            'project_folder_size_limit': project_folder_size_limit
        }

        return self.render_to_response(context)

    @staticmethod
    def get_folder_size(folder_path):
        """Calculate the total size of files in a folder."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                file_path = os.path.join(dirpath, f)
                total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)  # Return size in MB

    def post(self, request, *args, **kwargs):
        """
        Handle actions such as updating user information, notifications, or account.
        """
        action_map = {
            'update_user_info': self.update_user_info,
            'update_password': self.update_password,
            'update_notifications': self.update_notifications,
            'link_github': self.link_github,
            'unlink_github': self.unlink_github,
            'storage_limit': self.storage_limit,
            'update_docker_settings': self.update_docker_settings,
            'delete_account': self.delete_account,
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)
        return HttpResponse("Invalid action", status=400)

    @staticmethod
    def update_user_info(request):
        """Update user profile information."""
        user = request.user
        profile_picture = request.FILES.get('profile_picture', None)
        if profile_picture:
            fs = FileSystemStorage()
            filename = fs.save(profile_picture.name, profile_picture)
            user.profile_picture = fs.url(filename)

        username = request.POST.get('username')
        email = request.POST.get('email')
        bio = request.POST.get('bio')

        if username:
            user.username = username
        if email:
            user.email = email
        if bio is not None:
            user.bio = bio

        user.save()
        messages.success(request, "Your profile has been updated.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def update_password(request):
        """Update the user's password."""
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_new_password')

        # Check if the user has a password set (if no password is set, allow them to update)
        if request.user.password != '' and not request.user.check_password(current_password):
            messages.error(request, "Incorrect current password.")
            return redirect('settings', username=request.user.username)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('settings', username=request.user.username)

        user = request.user
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Keep user logged in after password change
        messages.success(request, "Your password has been updated.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def update_notifications(request):
        """Update notification preferences."""

        ActivityLog.objects.filter(user=request.user, activity_type='new_follower').update(
            notification_enabled='new_follower_notifications' in request.POST
        )
        ActivityLog.objects.filter(user=request.user, activity_type='new_task').update(
            notification_enabled='task_notifications' in request.POST
        )
        ActivityLog.objects.filter(user=request.user, activity_type='new_message').update(
            notification_enabled='message_notifications' in request.POST
        )
        ActivityLog.objects.filter(user=request.user, activity_type='project').update(
            notification_enabled='project_notifications' in request.POST
        )

        return redirect('settings', username=request.user.username)

    @staticmethod
    def clear_notifications(request):
        """Delete all notifications for the user."""
        ActivityLog.objects.filter(user=request.user).delete()
        messages.success(request, "All notifications and user activity has been deleted.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def link_github(request):
        """Handle linking the user's GitHub account."""
        user = request.user
        if user.is_authenticated:
            # Check if the user already has a linked GitHub account
            if user.social_auth.filter(provider='github').exists():
                messages.info(request, "Your GitHub account is already linked.")
            else:
                # You can trigger the GitHub login if the account is not linked
                messages.info(request, "You will now be redirected to link your GitHub account.")
                return redirect('social:begin', args=['github'])
        else:
            messages.error(request, "You must be logged in to link your GitHub account.")

        return redirect('settings', username=request.user.username)

    @staticmethod
    def unlink_github(request):
        """Handle unlinking the user's GitHub account."""
        user = request.user
        if user.is_authenticated:
            try:
                # Check if the user has a linked GitHub account
                github_account = user.social_auth.get(provider='github')
                github_account.delete()
                messages.success(request, "GitHub account unlinked successfully.")
            except UserSocialAuth.DoesNotExist:
                messages.info(request, "No linked GitHub account found.")
        else:
            messages.error(request, "You must be logged in to unlink your GitHub account.")

        return redirect('settings', username=request.user.username)

    @staticmethod
    def storage_limit(request):
        """Update storage limit for the user (admin only)."""
        user = request.user
        if not user.is_admin:
            messages.error(request, "You do not have permission to update Docker settings.")
            return redirect('settings', username=request.user.username)

        user.user_storage_limit = request.POST.get('project_folder_size_limit', user.user_storage_limit)

        user.save()
        messages.success(request, "Storage limit updated successfully.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def update_docker_settings(request):
        """Update Docker-related settings for the user (admin only)."""
        user = request.user
        if not user.is_admin:
            messages.error(request, "You do not have permission to update Docker settings.")
            return redirect('settings', username=request.user.username)

        user.default_mem_limit = request.POST.get('default_mem_limit', user.default_mem_limit)
        user.default_memswap_limit = request.POST.get('default_memswap_limit', user.default_memswap_limit)
        user.default_cpus = request.POST.get('default_cpus', user.default_cpus)
        user.default_cpu_shares = request.POST.get('default_cpu_shares', user.default_cpu_shares)

        user.save()
        messages.success(request, "Docker settings updated successfully.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def delete_account(request):
        """Delete the user's account."""
        password = request.POST.get('password')
        if not request.user.check_password(password):
            messages.error(request, "Incorrect password.")
            return redirect('settings', username=request.user.username)

        request.user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect('home')


class LoginView(View):
    """Handle user login by rendering login form and authenticating user."""
    template_name = 'login.html'

    def get(self, request):
        """Render login form."""
        return render(request, self.template_name)

    def post(self, request):
        """Authenticate user and log them in if credentials are valid."""
        username, password = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, 'Login successful!')

            if not user.password:
                return redirect('settings', username=request.user.username)

            return redirect('profile', username=request.user.username)

        messages.error(request, 'Invalid username or password')
        return redirect('login')


class RegisterView(View):
    """Handle user registration by rendering registration form and creating a new user."""
    template_name = 'register.html'

    def get(self, request):
        """Render registration form."""
        return render(request, self.template_name)

    def post(self, request):
        """Validate input and create a new user if no conflicts are found."""
        email, username, password = map(request.POST.get, ('email', 'username', 'password'))

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
        else:
            CustomUser.objects.create_user(username=username, email=email, password=password)
            messages.success(request, 'Registration successful! Please log in.')
            return redirect(reverse_lazy('login'))

        return redirect('register')


class GithubLoginView(View):
    """Handle GitHub login."""

    def get(self, request):
        user = request.user
        if user.is_authenticated:
            # Check if user has a GitHub account linked
            if user.social_auth.filter(provider='github').exists():
                messages.success(request, 'You are already logged in with GitHub!')
            else:
                messages.info(request, 'You can link your GitHub account now!')
        return redirect('social:begin', args=['github'])


class GithubRegisterView(View):
    """Handle GitHub registration."""

    def get(self, request):
        return redirect('social:begin', args=['github'])


class GithubCompleteRedirectView(View):
    """
    Handles the redirect from GitHub authentication
    """

    def get(self, request):
        user = request.user
        if user.is_authenticated:
            # Check if the GitHub account is already linked
            if user.social_auth.filter(provider='github').exists():
                messages.success(request, 'GitHub account is successfully linked to your profile!')
            else:
                messages.info(request, 'You can now link your GitHub account.')

        # You can redirect to the desired profile or home page
        return redirect('home')


class LogoutView(View):
    """Handle user logout."""

    def post(self, request, *args, **kwargs):
        """Log the user out and redirect to home page."""
        logout(request)
        return redirect('home')


class PasswordResetView(View):
    """Handle the password reset process by sending an email with a reset link."""

    def get(self, request):
        """Render password reset form."""
        return render(request, 'reset_password.html')

    def post(self, request):
        """Send password reset email if the email is associated with a user."""
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()

        if user:
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(
                reverse_lazy('password_reset_confirm', kwargs={'uidb64': user.pk, 'token': token}))

            send_mail(
                'Password Reset Request',
                render_to_string('password_reset_email.html', {'user': user, 'reset_link': reset_link}),
                SenderEmailSettings.objects.first().sender_email,
                [email]
            )
            messages.success(request, 'Password reset link has been sent to your email.')
            return redirect('login')

        messages.error(request, 'No user found with that email address.')
        return redirect('reset_password')


class ForgotUsernameView(View):
    """Handle the forgot username process by sending the username to the user's email."""

    def get(self, request):
        """Render forgot username form."""
        return render(request, 'reset_username.html')

    def post(self, request):
        """Send username to the email if it exists."""
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()

        if user:
            send_mail(
                'Forgot Username Request',
                render_to_string('username_reset_email.html', {'username': user.username}),
                SenderEmailSettings.objects.first().sender_email,
                [email]
            )
            messages.success(request, 'Your username has been sent to your email.')
            return redirect('login')

        messages.error(request, 'No user found with that email address.')
        return redirect('reset_username')
