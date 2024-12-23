# urls.py
from django.urls import path
from .views import IdeView, DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('ide/<int:project_id>/', IdeView.as_view(), name='ide'),
]

