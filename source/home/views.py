from django.shortcuts import redirect
from django.views.generic import TemplateView
from .models import HomePage

class LandingPageView(TemplateView):
    template_name = "home.html"

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for the landing page.
        Redirect logged-in users to their public profile page.
        """
        if request.user.is_authenticated:
            return redirect('profile', username=request.user.username)

        context = {
            'home': HomePage.objects.first()
        }

        return self.render_to_response(context)

