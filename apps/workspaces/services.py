import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.core.utils import model_update
from apps.currencies.models import Currency
from apps.workspaces.exceptions import WorkspaceCreationError, WorkspaceUpdateError
from apps.workspaces.models import Workspace, WorkspaceExchangeRate, WorkspaceTeam
from apps.workspaces.permissions import (
    assign_workspace_permissions,
    update_workspace_admin_group,
)
from guardian.shortcuts import remove_perm
from apps.core.permissions import WorkspacePermissions

logger = logging.getLogger(__name__)


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

        assign_workspace_permissions(
            workspace, request_user=orgMember.user if orgMember else None
        )

        # Log successful workspace creation
        try:
            user = orgMember.user if orgMember else None
            if user:
                BusinessAuditLogger.log_workspace_action(
                    user=user,
                    workspace=workspace,
                    action="create",
                    organization_id=str(organization.organization_id),
                    organization_title=organization.title,
                    created_by_member_id=str(orgMember.organization_member_id),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace creation: {log_error}", exc_info=True
            )

        return workspace
    except Exception as e:
        # Log workspace creation failure
        try:
            user = orgMember.user if orgMember else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_creation",
                    error=e,
                    organization_id=str(organization.organization_id),
                    organization_title=organization.title,
                    workspace_title=form.cleaned_data.get("title", "Unknown"),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace creation failure: {log_error}", exc_info=True
            )

        raise WorkspaceCreationError(f"Failed to create workspace: {str(e)}")


@transaction.atomic
def update_workspace_from_form(
    *,
    form,
    workspace: Workspace,
    previous_workspace_admin,
    previous_operations_reviewer,
    user=None,
) -> Workspace:
    """
    Updates a workspace from a form.
    """
    try:
        # Track what fields are being updated
        updated_fields = list(form.cleaned_data.keys())

        workspace = model_update(workspace, form.cleaned_data)
        new_workspace_admin = form.cleaned_data.get("workspace_admin")
        new_operations_reviewer = form.cleaned_data.get("operations_reviewer")
        update_workspace_admin_group(
            workspace,
            previous_workspace_admin,
            new_workspace_admin,
            previous_operations_reviewer,
            new_operations_reviewer,
            request_user=user,
        )

        # Log successful workspace update
        try:
            if user:
                BusinessAuditLogger.log_workspace_action(
                    user=user,
                    workspace=workspace,
                    action="update",
                    updated_fields=updated_fields,
                    previous_admin_id=str(
                        previous_workspace_admin.organization_member_id
                    )
                    if previous_workspace_admin
                    else None,
                    new_admin_id=str(new_workspace_admin.organization_member_id)
                    if new_workspace_admin
                    else None,
                    previous_reviewer_id=str(
                        previous_operations_reviewer.organization_member_id
                    )
                    if previous_operations_reviewer
                    else None,
                    new_reviewer_id=str(new_operations_reviewer.organization_member_id)
                    if new_operations_reviewer
                    else None,
                )
        except Exception as log_error:
            logger.error(f"Failed to log workspace update: {log_error}", exc_info=True)

        return workspace
    except Exception as e:
        # Log workspace update failure
        try:
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_update",
                    error=e,
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    attempted_updates=list(form.cleaned_data.keys()),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace update failure: {log_error}", exc_info=True
            )

        raise WorkspaceUpdateError(f"Failed to update workspace: {str(e)}")


def remove_team_from_workspace(workspace_team, user=None,team=None):
    try:
        # Store references before deletion
        workspace = workspace_team.workspace
        team = workspace_team.team
        #remove that team coordinator's view workspace teams under workspace permission
        if team.team_coordinator:
            remove_perm(WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE, team.team_coordinator.user, workspace)
        workspace_team.delete()

        # Log successful team removal from workspace
        try:
            if user:
                BusinessAuditLogger.log_workspace_team_action(
                    user=user,
                    workspace=workspace,
                    team=team,
                    action="remove",
                    removal_reason="Manual removal from workspace",
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace team removal: {log_error}", exc_info=True
            )

        return workspace_team
    except Exception as e:
        # Log workspace team removal failure
        try:
            if user and workspace_team:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_team_removal",
                    error=e,
                    workspace_id=str(workspace_team.workspace.workspace_id),
                    workspace_title=workspace_team.workspace.title,
                    team_id=str(workspace_team.team.team_id),
                    team_title=workspace_team.team.title,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace team removal failure: {log_error}",
                exc_info=True,
            )

        raise ValidationError(f"Failed to remove team from workspace: {str(e)}")


def add_team_to_workspace(
    workspace_id, team_id, custom_remittance_rate, workspace, user=None
):
    try:
        if custom_remittance_rate is None:
            custom_remittance_rate = workspace.remittance_rate

        workspace_team = WorkspaceTeam.objects.create(
            workspace_id=workspace_id,
            team_id=team_id,
            custom_remittance_rate=custom_remittance_rate,
        )

        # Log successful team addition to workspace
        try:
            if user:
                BusinessAuditLogger.log_workspace_team_action(
                    user=user,
                    workspace=workspace_team.workspace,
                    team=workspace_team.team,
                    action="add",
                    custom_remittance_rate=str(custom_remittance_rate)
                    if custom_remittance_rate
                    else None,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace team addition: {log_error}", exc_info=True
            )

        return workspace_team
    except Exception as e:
        # Log workspace team addition failure
        try:
            if user:
                from apps.teams.models import Team
                from apps.workspaces.models import Workspace

                workspace = Workspace.objects.get(workspace_id=workspace_id)
                team = Team.objects.get(team_id=team_id)

                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_team_addition",
                    error=e,
                    workspace_id=str(workspace_id),
                    workspace_title=workspace.title,
                    team_id=str(team_id),
                    team_title=team.title,
                    custom_remittance_rate=str(custom_remittance_rate)
                    if custom_remittance_rate
                    else None,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace team addition failure: {log_error}",
                exc_info=True,
            )

        raise


def update_workspace_team_remittance_rate_from_form(
    *, form, workspace_team, workspace, user=None
) -> WorkspaceTeam:
    try:
        # Store previous rate for logging
        previous_rate = workspace_team.custom_remittance_rate

        workspace_team = model_update(workspace_team, form.cleaned_data)
        if workspace_team.custom_remittance_rate == workspace.remittance_rate:
            workspace_team.custom_remittance_rate = None
        workspace_team.save()

        # Log successful remittance rate update
        try:
            if user:
                BusinessAuditLogger.log_workspace_team_action(
                    user=user,
                    workspace=workspace,
                    team=workspace_team.team,
                    action="remittance_rate_update",
                    previous_rate=str(previous_rate) if previous_rate else None,
                    new_rate=str(workspace_team.custom_remittance_rate)
                    if workspace_team.custom_remittance_rate
                    else None,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace team remittance rate update: {log_error}",
                exc_info=True,
            )

        return workspace_team
    except Exception as e:
        # Log remittance rate update failure
        try:
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_team_remittance_rate_update",
                    error=e,
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    team_id=str(workspace_team.team.team_id),
                    team_title=workspace_team.team.title,
                    attempted_rate=str(
                        form.cleaned_data.get("custom_remittance_rate", "Unknown")
                    ),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace team remittance rate update failure: {log_error}",
                exc_info=True,
            )

        raise


@transaction.atomic
def create_workspace_exchange_rate(
    *, workspace, organization_member, currency_code, rate, note, effective_date
):
    try:
        currency, _ = Currency.objects.get_or_create(code=currency_code)
        exchange_rate = WorkspaceExchangeRate.objects.create(
            workspace=workspace,
            currency=currency,
            rate=rate,
            effective_date=effective_date,
            added_by=organization_member,
            note=note,
        )

        # Log successful exchange rate creation
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_workspace_exchange_rate_action(
                    user=user,
                    exchange_rate=exchange_rate,
                    action="create",
                    currency_code=currency_code,
                    rate_value=str(rate),
                    effective_date_str=str(effective_date),
                    note_content=note,
                    added_by_member_id=str(organization_member.organization_member_id),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace exchange rate creation: {log_error}",
                exc_info=True,
            )

        return exchange_rate
    except IntegrityError as e:
        # Log exchange rate creation failure
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_exchange_rate_creation",
                    error=e,
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    currency_code=currency_code,
                    rate_value=str(rate),
                    effective_date_str=str(effective_date),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace exchange rate creation failure: {log_error}",
                exc_info=True,
            )

        raise ValidationError(f"Failed to create workspace exchange rate: {str(e)}")
    except Exception as e:
        # Log exchange rate creation failure
        try:
            user = organization_member.user if organization_member else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_exchange_rate_creation",
                    error=e,
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    currency_code=currency_code,
                    rate_value=str(rate),
                    effective_date_str=str(effective_date),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace exchange rate creation failure: {log_error}",
                exc_info=True,
            )

        raise ValidationError(f"Failed to create workspace exchange rate: {str(e)}")


@transaction.atomic
def update_workspace_exchange_rate(
    *, workspace_exchange_rate, note, is_approved, org_member
):
    try:
        # Store previous values for logging
        previous_note = workspace_exchange_rate.note
        previous_approval_status = workspace_exchange_rate.is_approved
        previous_approved_by = workspace_exchange_rate.approved_by

        workspace_exchange_rate = model_update(
            workspace_exchange_rate,
            {
                "note": note,
                "is_approved": is_approved,
                "approved_by": org_member if is_approved else None,
            },
        )

        # Log successful exchange rate update
        try:
            user = org_member.user if org_member else None
            if user:
                BusinessAuditLogger.log_workspace_exchange_rate_action(
                    user=user,
                    exchange_rate=workspace_exchange_rate,
                    action="update",
                    updated_fields=["note", "is_approved", "approved_by"],
                    previous_note=previous_note,
                    new_note=note,
                    previous_approval_status=previous_approval_status,
                    new_approval_status=is_approved,
                    previous_approved_by_id=str(
                        previous_approved_by.organization_member_id
                    )
                    if previous_approved_by
                    else None,
                    new_approved_by_id=str(org_member.organization_member_id)
                    if is_approved and org_member
                    else None,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace exchange rate update: {log_error}",
                exc_info=True,
            )

        return workspace_exchange_rate
    except Exception as e:
        # Log exchange rate update failure
        try:
            user = org_member.user if org_member else None
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_exchange_rate_update",
                    error=e,
                    exchange_rate_id=str(workspace_exchange_rate.id),
                    workspace_id=str(workspace_exchange_rate.workspace.workspace_id),
                    workspace_title=workspace_exchange_rate.workspace.title,
                    attempted_note=note,
                    attempted_approval_status=is_approved,
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace exchange rate update failure: {log_error}",
                exc_info=True,
            )

        raise ValidationError(f"Failed to update workspace exchange rate: {str(e)}")


def delete_workspace_exchange_rate(*, workspace_exchange_rate, user=None):
    try:
        # Store references before deletion
        exchange_rate_id = workspace_exchange_rate.id
        workspace = workspace_exchange_rate.workspace
        currency_code = workspace_exchange_rate.currency.code
        rate_value = workspace_exchange_rate.rate

        workspace_exchange_rate.delete()

        # Log successful exchange rate deletion
        try:
            if user:
                BusinessAuditLogger.log_workspace_exchange_rate_action(
                    user=user,
                    exchange_rate=None,  # Already deleted
                    action="delete",
                    deleted_exchange_rate_id=str(exchange_rate_id),
                    workspace_id=str(workspace.workspace_id),
                    workspace_title=workspace.title,
                    deleted_currency_code=currency_code,
                    deleted_rate_value=str(rate_value),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace exchange rate deletion: {log_error}",
                exc_info=True,
            )

    except Exception as e:
        # Log exchange rate deletion failure
        try:
            if user:
                BusinessAuditLogger.log_operation_failure(
                    user=user,
                    operation_type="workspace_exchange_rate_deletion",
                    error=e,
                    exchange_rate_id=str(workspace_exchange_rate.id),
                    workspace_id=str(workspace_exchange_rate.workspace.workspace_id),
                    workspace_title=workspace_exchange_rate.workspace.title,
                    currency_code=workspace_exchange_rate.currency.code,
                    rate_value=str(workspace_exchange_rate.rate),
                )
        except Exception as log_error:
            logger.error(
                f"Failed to log workspace exchange rate deletion failure: {log_error}",
                exc_info=True,
            )

        raise ValidationError(f"Failed to delete workspace exchange rate: {str(e)}")
