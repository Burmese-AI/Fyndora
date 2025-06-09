from django.urls import path
from apps.organizations.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
]
