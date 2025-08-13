from django.db import models


class TeamMemberRole(models.TextChoices):
    TEAM_COORDINATOR = "team_coordinator", "Team Coordinator"
    SUBMITTER = "submitter", "Submitter"
    AUDITOR = "auditor", "Auditor"
