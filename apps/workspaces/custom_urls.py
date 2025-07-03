from django.urls import path
from .views import SubmissionTeamListView


urlpatterns = [
    path(
        "submission-teams/",
        SubmissionTeamListView.as_view(),
        name="submission-teams",
    ),
]
