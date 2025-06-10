from django.db import models


class TeamMemberRole(models.TextChoices):
    WORKSPACE_ADMIN = "workspace_admin", "Workspace Admin"
    OPERATIONS_REVIEWER = "operations_reviewer", "Operations Reviewer"
    TEAM_COORDINATOR = "team_coordinator", "Team Coordinator"
    SUBMITTER = "submitter", "Submitter"
    AUDITOR = "auditor", "Auditor"
