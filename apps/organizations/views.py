from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from apps.organizations.models import Organization
from apps.organizations.selectors import get_user_organizations


# Create your views here.


class HomeView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/home.html"
    context_object_name = "organizations"

    def get_queryset(self):
        return get_user_organizations(self.request.user)
