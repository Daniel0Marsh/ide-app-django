from django.urls import path
from .views import LoginView, RegisterView, LogoutView, PasswordResetView, ForgotUsernameView, GithubCompleteRedirectView, SettingsView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('reset_password/', PasswordResetView.as_view(), name='reset_password'),
    path('reset_username/', ForgotUsernameView.as_view(), name='reset_username'),
    path("settings/<str:username>/", SettingsView.as_view(), name="settings"),
    path('auth/complete/github/dashboard/', GithubCompleteRedirectView.as_view(), name='github_complete_redirect'),
]
