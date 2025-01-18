from django.urls import path
from .views import ProfileView, SearchView

urlpatterns = [
    path("profile/<str:username>/", ProfileView.as_view(), name="profile"),
    path("profile/<str:username>/activities/", ProfileView.user_activity_ajax, name="user_activity_ajax"),
    path('search/', SearchView.as_view(), name='search'),
]
