from decimal import Decimal
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.entries.models import Entry
from apps.remittance.models import Remittance


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

    workspace_team = instance.workspace_team
    if not workspace_team:
        return

    team = workspace_team.team
    workspace = workspace_team.workspace

    # Calculate the remittance rate (team's custom rate or workspace default)
    rate = (
        team.custom_remittance_rate
        if team.custom_remittance_rate is not None
        else workspace.remittance_rate
    )
    if rate is None:
        return

    remittance_rate = Decimal(str(rate)) / Decimal("100.00")

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
