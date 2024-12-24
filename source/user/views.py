from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View


class LoginView(View):
    """Custom LoginView to handle user login."""
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect(reverse_lazy('dashboard'))
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')


class RegisterView(View):
    """Custom registration view to handle user registration."""
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return redirect('register')

        User.objects.create_user(username=username, email=email, password=password)
        return redirect(reverse_lazy('login'))


class LogoutView(View):
    """Handle logout with a redirect after logging out."""

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')