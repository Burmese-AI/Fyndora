from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from apps.core.utils import model_update
from apps.teams.constants import TeamMemberRole
from apps.auditlog.services import audit_create

from .models import Entry


def entry_create(*, submitted_by, entry_type, amount, description, workspace=None, workspace_team=None):
    """
    Service to create a new entry.
    """
    if submitted_by.role != TeamMemberRole.SUBMITTER:
        raise ValueError("Only users with Submitter role can create entries.")

    if amount <= Decimal("0.00"):
        raise ValidationError("Amount must be greater than zero.")

    entry_data = {
        "entry_type": entry_type,
        "amount": amount,
        "description": description,
        "submitter_content_type": ContentType.objects.get_for_model(submitted_by),
        "submitter_object_id": submitted_by.pk,
        "workspace": workspace,
        "workspace_team": workspace_team,
    }

    entry = Entry()

    # transaction.atomic ensures all-or-nothing operation
    with transaction.atomic():
        entry = model_update(entry, entry_data)

        # Create audit trail
        audit_create(
            user=submitted_by.organization_member.user,
            action_type="entry_created",
            target_entity=entry,
            metadata={
                "entry_type": entry_type,
                "amount": str(amount),
                "description": description,
            },
        )

    return entry
