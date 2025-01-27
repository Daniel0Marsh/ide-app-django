from django.urls import path
from .views import ProjectView, IdeView

urlpatterns = [
    path('<str:username>/<str:project_name>/', ProjectView.as_view(), name='project'),
    path('<str:username>/<str:project_name>/editor', IdeView.as_view(), name='ide'),
]
