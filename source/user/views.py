from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import CustomUser, SenderEmailSettings
from social_django.utils import psa


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
            return redirect(reverse_lazy('profile', kwargs={'username': username}))

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
            reset_link = request.build_absolute_uri(reverse_lazy('password_reset_confirm', kwargs={'uidb64': user.pk, 'token': token}))

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
