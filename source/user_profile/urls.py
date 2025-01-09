from django.urls import path
from .views import ProfileView, SearchView

urlpatterns = [
    path('', ProfileView.as_view(), name="personal_profile"),
    path("profile/<str:username>/", ProfileView.as_view(), name="public_profile"),
    path('search/', SearchView.as_view(), name='search'),
]
