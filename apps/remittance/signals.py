from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.entries.models import Entry
from apps.remittance.models import Remittance
from apps.workspaces.models import WorkspaceTeam


@receiver(post_save, sender=Entry)
def calculate_remittance_on_income(sender, instance, created, **kwargs):
    """
    Signal handler to automatically calculate remittance due when an income entry is submitted.

    This handler will:
    1. Only trigger for newly created income entries
    2. Find the appropriate remittance rate (team's custom rate or workspace default)
    3. Calculate the due amount based on the income amount and remittance rate
    4. Create or update a remittance record
    """
    if not created or instance.entry_type != "income":
        return

    # Get the team member who submitted the entry
    team_member = instance.submitted_by

    # Get the team and workspace through the team member
    team = team_member.team

    # Find the workspace team relationship
    try:
        workspace_team = WorkspaceTeam.objects.get(
            team=team,
            workspace__organization=team_member.organization_member.organization,
        )
        workspace = workspace_team.workspace
    except WorkspaceTeam.DoesNotExist:
        # If no workspace team is found, we can't proceed with remittance calculation
        return

    # Calculate the remittance rate (team's custom rate or workspace default)
    remittance_rate = (
        team.custom_remittance_rate
        if team.custom_remittance_rate is not None
        else workspace.remittance_rate
    ) / 100  # Convert percentage to decimal

    # Calculate the due amount
    due_amount = instance.amount * remittance_rate

    # Create or update the remittance record
    with transaction.atomic():
        Remittance.objects.update_or_create(
            workspace_team=workspace_team,
            defaults={
                "due_amount": due_amount,
                "status": "pending",
            },
        )
