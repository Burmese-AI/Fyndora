from django.urls import path
from apps.organizations.views import HomeView, OrganizationDetailView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("<uuid:pk>/", OrganizationDetailView.as_view(), name="organization_detail"),
]
