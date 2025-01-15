from django.urls import path
from .views import ProjectView, IdeView

urlpatterns = [
    path('project/<str:username>/<int:project_id>/', ProjectView.as_view(), name='project'),
    path('ide/<str:username>/<int:project_id>/', IdeView.as_view(), name='ide'),
]
