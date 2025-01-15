from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from .models import CustomUser


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
        email, username, password = request.POST.get('email'), request.POST.get('username'), request.POST.get(
            'password')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
        else:
            CustomUser.objects.create_user(username=username, email=email, password=password)
            messages.success(request, 'Registration successful! Please log in.')
            return redirect(reverse_lazy('login'))

        return redirect('register')


class LogoutView(View):
    """Handle user logout."""

    def post(self, request, *args, **kwargs):
        """Log the user out and redirect to home page."""
        logout(request)
        return redirect('home')
