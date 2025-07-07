from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def entry_update_url(entry, organization, workspace=None, workspace_team=None):
    if workspace_team:
        return reverse(
            "workspace_team_entry_update",
            kwargs={
                "organization_id": organization.pk,
                "workspace_id": workspace.pk,
                "workspace_team_id": workspace_team.pk,
                "pk": entry.pk,
            }
        )
    if workspace:
        return reverse(
            "workspace_expense_update",
            kwargs={
                "organization_id": organization.pk,
                "workspace_id": workspace.pk,
                "pk": entry.pk,
            },
        )
    return reverse(
        "organization_expense_update",
        kwargs={"organization_id": organization.pk, "pk": entry.pk},
    )
