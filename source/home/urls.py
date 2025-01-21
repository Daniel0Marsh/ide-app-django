from django.urls import path
from .views import LandingPageView

urlpatterns = [
    path('', LandingPageView.as_view(), name='home'),
]

# Custom error handlers
handler404 = 'home.views.custom_page_not_found_view'
handler403 = 'home.views.custom_permission_denied_view'
handler400 = 'home.views.custom_bad_request_view'
handler500 = 'home.views.custom_error_view'
