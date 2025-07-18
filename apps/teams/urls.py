from django.urls import path
from . import views


urlpatterns = [
    path("", views.teams_view, name="teams"),
    path("create/", views.create_team_view, name="create_team"),
    path("edit/<uuid:team_id>/", views.edit_team_view, name="edit_team"),
    path(
        "team_members/<uuid:team_id>/", views.get_team_members_view, name="team_members"
    ),
    path(
        "add_team_member/<uuid:team_id>/",
        views.add_team_member_view,
        name="add_team_member",
    ),
    path(
        "remove_team_member/<uuid:team_id>/<uuid:team_member_id>/",
        views.remove_team_member_view,
        name="remove_team_member",
    ),
    path(
        "edit_team_member_role/<uuid:team_id>/<uuid:team_member_id>/",
        views.edit_team_member_role_view,
        name="edit_team_member_role",
    ),
]
