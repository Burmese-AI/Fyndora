from django import template
from django.urls import reverse
from ..constants import EntryType

register = template.Library()


@register.simple_tag
def entry_delete_url(entry_type, entry):
    if entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT, EntryType.REMITTANCE]:
        return reverse(
            "workspace_team_entry_delete",
            kwargs={
                "organization_id": entry.organization.pk,
                "workspace_id": entry.workspace.pk,
                "workspace_team_id": entry.workspace_team.pk,
                "pk": entry.pk,
            },
        )
    elif entry_type == EntryType.ORG_EXP:
        return reverse(
            "organization_expense_delete",
            kwargs={"organization_id": entry.organization.pk, "pk": entry.pk},
        )
    elif entry_type == EntryType.WORKSPACE_EXP:
        return reverse(
            "workspace_expense_delete",
            kwargs={
                "organization_id": entry.organization.pk,
                "workspace_id": entry.workspace.pk,
                "pk": entry.pk,
            },
        )
    return ""


@register.simple_tag
def entry_update_url(entry_type, entry):
    if entry_type in [EntryType.INCOME, EntryType.DISBURSEMENT, EntryType.REMITTANCE]:
        return reverse(
            "workspace_team_entry_update",
            kwargs={
                "organization_id": entry.organization.pk,
                "workspace_id": entry.workspace.pk,
                "workspace_team_id": entry.workspace_team.pk,
                "pk": entry.pk,
            },
        )
    elif entry_type == EntryType.ORG_EXP:
        return reverse(
            "organization_expense_update",
            kwargs={"organization_id": entry.organization.pk, "pk": entry.pk},
        )
    elif entry_type == EntryType.WORKSPACE_EXP:
        return reverse(
            "workspace_expense_update",
            kwargs={
                "organization_id": entry.organization.pk,
                "workspace_id": entry.workspace.pk,
                "pk": entry.pk,
            },
        )
    return ""
