from django.urls import path
from .views import IdeView

urlpatterns = [
    path('', IdeView.as_view(), name='project')
]