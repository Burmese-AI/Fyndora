from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from apps.organizations.models import Organization


# Create your views here.


class HomeView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/home.html"
    context_object_name = "organizations"

    def get_queryset(self):
        organizations = Organization.objects.filter(
            members__user_id=self.request.user, members__is_active=True
        )
        return organizations
