# urls.py
from django.urls import path
from .views import IdeView

urlpatterns = [
    path('ide/<int:project_id>/', IdeView.as_view(), name='ide'),
]

