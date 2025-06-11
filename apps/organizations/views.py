from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from apps.organizations.models import Organization
from apps.organizations.selectors import get_user_organization


# Create your views here.


class HomeView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/home.html"
    context_object_name = "organizations"

    def get_queryset(self):
        try:
            return get_user_organization(self.request.user)
        except Exception as e:
            # Log the error here if you have a logging system
            raise PermissionDenied("Unable to fetch organizations. Please try again later.")
