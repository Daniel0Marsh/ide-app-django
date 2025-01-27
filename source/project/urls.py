from django.urls import path
from .views import ProjectView, IdeView

urlpatterns = [
    path('<str:username>/<int:project_id>/', ProjectView.as_view(), name='project'),
    path('<str:username>/<int:project_id>/editor', IdeView.as_view(), name='ide'),
]
