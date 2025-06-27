from django.urls import path
from . import views


urlpatterns = [
    path("", views.teams_view, name="teams"),
    path("create/", views.create_team_view, name="create_team"),
]
