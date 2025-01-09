from django.urls import path
from .views import ProfileView, SearchView

urlpatterns = [
    path("profile/<str:username>/", ProfileView.as_view(), name="public_profile"),
    path('search/', SearchView.as_view(), name='search'),
]
