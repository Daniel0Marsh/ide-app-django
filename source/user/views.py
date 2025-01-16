from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import CustomUser, SenderEmailSettings
from social_django.utils import psa
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.views.generic import TemplateView, View


class SettingsView(TemplateView):
    """Handle settings page where user can update their details and set password."""
    template_name = 'settings.html'

    def get(self, request, *args, **kwargs):
        """Render settings form with user details and password input."""

        context = {
            'needs_password': not request.user.password or request.user.password == ' ',
            'user': request.user,
        }

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Handle actions such as updating user information.
        """
        action_map = {
            'update_password': self.update_password,
            'update_username': self.update_username,
            'update_email': self.update_email,
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)
        return HttpResponse("Invalid action", status=400)

    def update_password(self, request):
        """Update the user's password."""
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('settings')

        user = request.user
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Keep user logged in after password change
        messages.success(request, "Your password has been updated.")
        return redirect('settings')

    def update_username(self, request):
        """Update the user's username."""
        new_username = request.POST.get('new_username')
        user = request.user

        if User.objects.filter(username=new_username).exists():
            messages.error(request, "Username already taken.")
            return redirect('settings')

        user.username = new_username
        user.save()
        messages.success(request, "Your username has been updated.")
        return redirect('settings')

    def update_email(self, request):
        """Update the user's email."""
        new_email = request.POST.get('new_email')
        user = request.user

        if User.objects.filter(email=new_email).exists():
            messages.error(request, "Email is already in use.")
            return redirect('settings')

        user.email = new_email
        user.save()
        messages.success(request, "Your email has been updated.")
        return redirect('settings')


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
