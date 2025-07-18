"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.organizations.urls")),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("auditlog/", include("apps.auditlog.urls")),
    path("<uuid:organization_id>/workspaces/", include("apps.workspaces.urls")),
    path("<uuid:organization_id>/", include("apps.workspaces.custom_urls")),
    path("invitations/", include("apps.invitations.urls")),
    path("<uuid:organization_id>/teams/", include("apps.teams.urls")),
    path("remittances/", include("apps.remittance.urls")),
    path("<uuid:organization_id>/", include("apps.entries.urls")),
    path("attachments/", include("apps.attachments.urls")),
]
