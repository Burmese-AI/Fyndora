from django.urls import path
from apps.organizations.views import HomeView, OrganizationDetailView, organization_create

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("create/", organization_create, name="organization_create"),
    path("<uuid:pk>/", OrganizationDetailView.as_view(), name="organization_detail"),
    
]
