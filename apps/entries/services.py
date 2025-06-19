from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.utils import model_update
from apps.teams.constants import TeamMemberRole
from apps.auditlog.services import audit_create

from .models import Entry
from .constants import EntryType
from django.contrib.contenttypes.models import ContentType


def create_org_expense_entry(*, org_member, amount, description):
    entry = Entry(
        submitter_content_type=ContentType.objects.get_for_model(org_member),
        submitter_object_id=org_member.pk,
        entry_type=EntryType.ORG_EXP,
        amount=amount,
        description=description,
    )
    
    entry.full_clean()
    entry.save()
    
    return entry

def entry_create(*, submitted_by, entry_type, amount, description):
    """
    Service to create a new entry.
    """
    if submitted_by.role != TeamMemberRole.SUBMITTER:
        raise ValueError("Only users with Submitter role can create entries.")

    if amount <= Decimal("0.00"):
        raise ValidationError("Amount must be greater than zero.")

    entry_data = {
        "submitted_by": submitted_by,
        "entry_type": entry_type,
        "amount": amount,
        "description": description,
    }

    entry = Entry()

    # transaction.atomic ensures all-or-nothing operation
    with transaction.atomic():
        entry = model_update(entry, entry_data)

        # Create audit trail
        audit_create(
            user=submitted_by.organization_member.user,
            action_type="entry_created",
            target_entity=entry.entry_id,
            target_entity_type="entry",
            metadata={
                "entry_type": entry_type,
                "amount": str(amount),
                "description": description,
            },
        )

    return entry
