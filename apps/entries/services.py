from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.utils import model_update
from apps.teams.constants import TeamMemberRole
from apps.auditlog.services import audit_create

from .models import Entry
from .constants import EntryType, EntryStatus
from apps.core.utils import percent_change
from .selectors import get_this_month_org_expenses, get_last_month_org_expenses, get_average_monthly_org_expenses, get_total_org_expenses

def create_org_expense_entry(*, org_member, amount, description):
    print(f"org_member: {org_member}")
    entry = Entry.objects.create(
        entry_type=EntryType.ORG_EXP,
        amount=amount,
        description=description,
        submitter=org_member,
        status=EntryStatus.APPROVED
    )
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

def get_org_expense_stats(organization):
    total = get_total_org_expenses(organization)
    this_month = get_this_month_org_expenses(organization)
    last_month = get_last_month_org_expenses(organization)
    avg_monthly = get_average_monthly_org_expenses(organization)

    return [
        {
            "title": "Total Expenses",
            "value": f"${total:,.0f}",
            "subtitle": percent_change(total, last_month),
            "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z"/></svg>'
        },
        {
            "title": "This Month’s Expenses",
            "value": f"${this_month:,.0f}",
            "subtitle": percent_change(this_month, last_month),
            "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6h.008v.008H12v-.008ZM12 15h.008v.008H12V15Zm0 2.25h.008v.008H12v-.008ZM9.75 15h.008v.008H9.75V15Zm0 2.25h.008v.008H9.75v-.008ZM7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm6.75-4.5h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V15Zm0 2.25h.008v.008h-.008v-.008Zm2.25-4.5h.008v.008H16.5v-.008Zm0 2.25h.008v.008H16.5V15Z"/></svg>'
        },
        {
            "title": "Average Monthly Expense",
            "value": f"${avg_monthly:,.0f}",
            "subtitle": percent_change(this_month, avg_monthly),
            "icon": '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"/></svg>'
        },
    ]