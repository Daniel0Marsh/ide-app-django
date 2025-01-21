from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from .models import HomePage


class LandingPageView(TemplateView):
    template_name = "home.html"

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the landing page.
        """
        if request.user.is_authenticated:
            return redirect('profile', username=request.user.username)

        context = {
            'home': HomePage.objects.first()
        }

        return self.render_to_response(context)


def custom_page_not_found_view(request, exception):
    return render(request, '404.html', status=404)


def custom_permission_denied_view(request, exception=None):
    return render(request, '403.html', status=403)


def custom_bad_request_view(request, exception=None):
    return render(request, '400.html', status=400)


def custom_error_view(request):
    return render(request, '500.html', status=500)
