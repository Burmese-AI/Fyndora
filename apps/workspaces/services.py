from django.db import transaction
from apps.currencies.models import Currency
from apps.workspaces.models import Workspace, WorkspaceExchangeRate
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.core.utils import model_update
from django.core.exceptions import ValidationError
from apps.workspaces.models import WorkspaceTeam
from apps.workspaces.permissions import (
    assign_workspace_permissions,
    update_workspace_admin_group,
)
from django.db.utils import IntegrityError


@transaction.atomic
def create_workspace_from_form(*, form, orgMember, organization) -> Workspace:
    """
    Creates a new workspace from a form and assigns it to an organization.

    Args:
        form: WorkspaceForm instance (already validated)
        organization: Organization instance the workspace belongs to

    Returns:
        Workspace: The created workspace instance
    """
    try:
        workspace = form.save(commit=False)
        workspace.organization = organization
        workspace.created_by = orgMember
        workspace.save()

        assign_workspace_permissions(workspace)
        return workspace
    except Exception as e:
        raise WorkspaceCreationError(f"Failed to create workspace: {str(e)}")


@transaction.atomic
def update_workspace_from_form(
    *, form, workspace, previous_workspace_admin, previous_operations_reviewer
) -> Workspace:
    """
    Updates a workspace from a form.
    """
    try:
        workspace = model_update(workspace, form.cleaned_data)
        new_workspace_admin = form.cleaned_data.get("workspace_admin")
        new_operations_reviewer = form.cleaned_data.get("operations_reviewer")
        update_workspace_admin_group(
            workspace,
            previous_workspace_admin,
            new_workspace_admin,
            previous_operations_reviewer,
            new_operations_reviewer,
        )

        return workspace
    except Exception as e:
        raise WorkspaceUpdateError(f"Failed to update workspace: {str(e)}")


def remove_team_from_workspace(workspace_id, team_id):
    workspace_team = WorkspaceTeam.objects.get(
        workspace_id=workspace_id, team_id=team_id
    )
    workspace_team.delete()
    return workspace_team


def add_team_to_workspace(workspace_id, team_id, custom_remittance_rate):
    workspace_team = WorkspaceTeam.objects.create(
        workspace_id=workspace_id,
        team_id=team_id,
        custom_remittance_rate=custom_remittance_rate,
    )
    return workspace_team


def update_workspace_team_remittance_rate_from_form(
    *, form, workspace_team, workspace
) -> WorkspaceTeam:
    workspace_team = model_update(workspace_team, form.cleaned_data)
    if workspace_team.custom_remittance_rate == workspace.remittance_rate:
        workspace_team.custom_remittance_rate = None
    workspace_team.save()
    return workspace_team


@transaction.atomic
def create_workspace_exchange_rate(
    *, workspace, organization_member, currency_code, rate, note, effective_date
):
    try:
        currency, _ = Currency.objects.get_or_create(code=currency_code)
        WorkspaceExchangeRate.objects.create(
            workspace=workspace,
            currency=currency,
            rate=rate,
            effective_date=effective_date,
            added_by=organization_member,
            note=note,
        )
    except IntegrityError as e:
        raise ValidationError(f"Failed to create workspace exchange rate: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Failed to create workspace exchange rate: {str(e)}")


@transaction.atomic
def update_workspace_exchange_rate(
    *, workspace_exchange_rate, note, is_approved, org_member
):
    try:
        workspace_exchange_rate = model_update(
            workspace_exchange_rate,
            {
                "note": note,
                "is_approved": is_approved,
                "approved_by": org_member if is_approved else None,
            },
        )
        return workspace_exchange_rate
    except Exception as e:
        raise ValidationError(f"Failed to update workspace exchange rate: {str(e)}")


def delete_workspace_exchange_rate(*, workspace_exchange_rate):
    try:
        workspace_exchange_rate.delete()
    except Exception as e:
        raise ValidationError(f"Failed to delete workspace exchange rate: {str(e)}")
