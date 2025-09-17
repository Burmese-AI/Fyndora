import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from guardian.shortcuts import assign_perm
from apps.workspaces.models import WorkspaceTeam

from apps.auditlog.business_logger import BusinessAuditLogger
from apps.core.utils import model_update
from apps.teams.exceptions import (
    TeamCreationError,
    TeamMemberCreationError,
    TeamMemberDeletionError,
    TeamMemberUpdateError,
    TeamUpdateError,
)
from apps.teams.permissions import (
    assign_team_permissions,
    update_team_coordinator_group,
)
from apps.core.permissions import WorkspacePermissions
from guardian.shortcuts import remove_perm

from .models import Team, TeamMember
from .constants import TeamMemberRole

logger = logging.getLogger(__name__)


def create_team_from_form(form, organization, orgMember):
    try:
        team = form.save(commit=False)
        team.organization = organization
        team.created_by = orgMember
        # Set audit context to prevent duplicate logging from signal handlers
        team._audit_user = orgMember.user
        team.save()

        if team.team_coordinator:
            TeamMember.objects.create(
                team=team,
                organization_member=team.team_coordinator,
                role=TeamMemberRole.TEAM_COORDINATOR,
            )

        assign_team_permissions(team)

        # CRUD logging handled by signal handlers

        return team
    except Exception as e:
        # Audit logging: Log team creation failure
        try:
            BusinessAuditLogger.log_operation_failure(
                user=orgMember.user,
                operation_type="team_creation",
                error=e,
                request=None,
                organization_id=str(organization.organization_id),
                organization_title=organization.title,
                attempted_team_title=form.cleaned_data.get("title", "Unknown")
                if form.cleaned_data
                else "Unknown",
            )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for team creation failure: {audit_error}",
                exc_info=True,
            )
        raise TeamCreationError(f"An error occurred while creating team: {str(e)}")


User = get_user_model()


# @transaction.atomic
# def team_member_add(
#     *, added_by: User, org_member: OrganizationMember, team: Team, role: str
# ) -> TeamMember:
#     """
#     Adds an organization member to a team with a specific role and assigns all the
#     necessary permissions for that role using Django groups.
#     """
#     try:
#         role = role.upper()

#         team_member, _ = TeamMember.objects.update_or_create(
#             organization_member=org_member, team=team, defaults={"role": role}
#         )

#         workspace = team.workspace

#         group_name = f"{workspace.workspace_id}_{team.team_id}_{role}"
#         group, created = Group.objects.get_or_create(name=group_name)

#         if created:
#             permissions = get_permissions_for_role(role)
#             for perm in permissions:
#                 assign_perm(perm, group, workspace)

#         group.user_set.add(org_member.user)

#         # Audit logging: Log team member addition
#         try:
#             BusinessAuditLogger.log_team_member_action(
#                 user=added_by,
#                 team_member=team_member,
#                 action="add",
#                 request=None,
#                 operation_type="team_member_addition",
#                 role=role,
#                 group_created=created,
#                 group_name=group_name,
#                 permissions_assigned=len(permissions) if created else 0,
#             )
#         except Exception as audit_error:
#             logger.error(
#                 f"Audit logging failed for team member addition: {audit_error}",
#                 exc_info=True,
#             )

#         return team_member
#     except Exception as e:
#         # Audit logging: Log team member addition failure
#         try:
#             BusinessAuditLogger.log_operation_failure(
#                 user=added_by,
#                 operation_type="team_member_addition",
#                 error=e,
#                 request=None,
#                 team_id=str(team.team_id),
#                 team_title=team.title,
#                 target_member_email=org_member.user.email,
#                 attempted_role=role,
#             )
#         except Exception as audit_error:
#             logger.error(
#                 f"Audit logging failed for team member addition failure: {audit_error}",
#                 exc_info=True,
#             )
#         raise TeamMemberCreationError(
#             f"An error occurred while adding team member: {str(e)}"
#         )


def create_team_member_from_form(form, team, organization):
    try:
        team_member = form.save(commit=False)
        team_member.team = team
        team_member.organization = organization
        # Set audit context to prevent duplicate logging from signal handlers
        team_member._audit_user = team_member.organization_member.user
        team_member.save()

        # CRUD logging handled by signal handlers

        return team_member
    except Exception as e:
        # Audit logging: Log team member creation failure
        try:
            # Try to get user from form data or use a fallback
            current_user = None
            if hasattr(form, "cleaned_data") and form.cleaned_data:
                org_member = form.cleaned_data.get("organization_member")
                if org_member:
                    current_user = org_member.user

            if current_user:
                BusinessAuditLogger.log_operation_failure(
                    user=current_user,
                    operation_type="team_member_form_creation",
                    error=e,
                    request=None,
                    team_id=str(team.team_id),
                    team_title=team.title,
                    organization_id=str(organization.organization_id),
                    organization_title=organization.title,
                )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for team member creation failure: {audit_error}",
                exc_info=True,
            )
        raise TeamMemberCreationError(
            f"An error occurred while creating team member: {str(e)}"
        )


@transaction.atomic
def update_team_member_role(
    *, form, team_member, previous_role, team, user=None
) -> TeamMember:
    """
    Updates a team member role from a form.
    """
    try:
        new_role = form.cleaned_data["role"]
        logger.debug(
            f"Team member role update - Previous role: {previous_role}, New role: {new_role}"
        )

        if previous_role == "team_coordinator":
            team.team_coordinator = None
            team.save()
            update_team_coordinator_group(team, team_member.organization_member, None)
        # Set audit context to prevent duplicate logging from signal handlers
        current_user = user if user else team_member.organization_member.user
        team_member._audit_user = current_user
        team_member = model_update(team_member, {"role": form.cleaned_data["role"]})

        # Business logic logging: Log role changes
        try:
            BusinessAuditLogger.log_team_member_action(
                user=current_user,
                team_member=team_member,
                action="role_change",
                request=None,
                operation_type="team_member_role_update",
                previous_role=previous_role,
                new_role=new_role,
                coordinator_change=previous_role == "team_coordinator",
            )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for team member role update: {audit_error}",
                exc_info=True,
            )
        # General CRUD logging handled by signal handlers

        return team_member
    except Exception as e:
        # Audit logging: Log team member role update failure
        try:
            BusinessAuditLogger.log_operation_failure(
                user=current_user,
                operation_type="team_member_role_update",
                error=e,
                request=None,
                team_id=str(team.team_id),
                team_title=team.title,
                team_member_id=str(team_member.pk),
                member_email=team_member.organization_member.user.email,
                attempted_role_change=f"{previous_role} -> {form.cleaned_data.get('role', 'Unknown')}",
            )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for team member role update failure: {audit_error}",
                exc_info=True,
            )
        raise TeamMemberUpdateError(f"Failed to update team member: {str(e)}")


def update_team_from_form(
    form, team, organization, previous_team_coordinator, user=None
) -> Team:
    """
    Updates a team from a form.
    """
    try:
        # Set audit context to prevent duplicate logging from signal handlers
        current_user = user if user else team.created_by.user
        team._audit_user = current_user
        team = model_update(team, form.cleaned_data)
        new_team_coordinator = team.team_coordinator
        coordinator_changed = previous_team_coordinator != new_team_coordinator

        # Business logic logging: Log coordinator changes if applicable
        if coordinator_changed:
            try:
                BusinessAuditLogger.log_team_action(
                    user=current_user,
                    team=team,
                    action="coordinator_change",
                    request=None,
                    operation_type="team_coordinator_update",
                    coordinator_changed=coordinator_changed,
                    previous_coordinator_email=previous_team_coordinator.user.email
                    if previous_team_coordinator
                    else None,
                    new_coordinator_email=new_team_coordinator.user.email
                    if new_team_coordinator
                    else None,
                )
            except Exception as audit_error:
                logger.error(
                    f"Audit logging failed for team coordinator change: {audit_error}",
                    exc_info=True,
                )
        # General CRUD logging handled by signal handlers
        # which means the team coordinator is not being changed.. MgMg still MgMg
        if previous_team_coordinator == new_team_coordinator:
            # just return the team and do nothing
            return team

        # which means the team coordinator is being removed
        if new_team_coordinator is None:
            team.team_coordinator = None
            team.save()
            update_team_coordinator_group(team, previous_team_coordinator, None)
            team_member = TeamMember.objects.get(
                team=team,
                organization_member=previous_team_coordinator,
                role="team_coordinator",
            )
            workspace_teams = WorkspaceTeam.objects.filter(team=team)
            for workspace_team in workspace_teams:
                workspace_team_group_name = (
                    f"Workspace Team - {workspace_team.workspace_team_id}"
                )
                workspace_team_group, _ = Group.objects.get_or_create(
                    name=workspace_team_group_name
                )
                workspace_team_group.user_set.remove(previous_team_coordinator.user)
                print(
                    "Team coordinator removed from workspace team group permission removed"
                )
            # Set audit user for signal handler to capture coordinator removal metadata
            team_member._audit_user = current_user
            team_member.delete()
            return team

        # which means the team coordinator is changed with a new one
        if new_team_coordinator is not None:
            team_member = TeamMember.objects.create(
                team=team,
                organization_member=new_team_coordinator,
                role="team_coordinator",
            )
            joined_workspaces = WorkspaceTeam.objects.filter(team=team)
            for workspace_team in joined_workspaces:
                assign_perm(
                    WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE,
                    new_team_coordinator.user,
                    workspace_team.workspace,
                )
                print(
                    "successfully assigned view workspace teams under workspace permission to new team coordinator"
                )
            # Audit logging: Log new coordinator addition
            try:
                BusinessAuditLogger.log_team_member_action(
                    user=current_user,
                    team_member=team_member,
                    action="add",
                    request=None,
                    operation_type="team_coordinator_assignment",
                    role="team_coordinator",
                    assignment_context="team_update",
                )
            except Exception as audit_error:
                logger.error(
                    f"Audit logging failed for coordinator assignment: {audit_error}",
                    exc_info=True,
                )

            if previous_team_coordinator is not None:
                old_team_member = TeamMember.objects.get(
                    team=team,
                    organization_member=previous_team_coordinator,
                    role="team_coordinator",
                )
                joined_workspaces = WorkspaceTeam.objects.filter(team=team)
                for workspace_team in joined_workspaces:
                    remove_perm(
                        WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE,
                        previous_team_coordinator.user,
                        workspace_team.workspace,
                    )
                    print(
                        "successfully removed view workspace teams under workspace permission from previous team coordinator"
                    )

                # Audit logging: Log previous coordinator removal
                try:
                    BusinessAuditLogger.log_team_member_action(
                        user=current_user,
                        team_member=old_team_member,
                        action="remove",
                        request=None,
                        operation_type="team_coordinator_replacement",
                        reason="coordinator_replaced",
                        replacement_context="team_update",
                        new_coordinator_email=new_team_coordinator.user.email,
                    )
                except Exception as audit_error:
                    logger.error(
                        f"Audit logging failed for coordinator replacement: {audit_error}",
                        exc_info=True,
                    )

                old_team_member.delete()
            update_team_coordinator_group(
                team, previous_team_coordinator, new_team_coordinator
            )
            print("New team coordinator", team.team_coordinator)
            workspace_teams = WorkspaceTeam.objects.filter(team=team)
            print("workspace_teams", workspace_teams)
            for workspace_team in workspace_teams:
                workspace_team_group_name = (
                    f"Workspace Team - {workspace_team.workspace_team_id}"
                )
                workspace_team_group, _ = Group.objects.get_or_create(
                    name=workspace_team_group_name
                )
                workspace_team_group.user_set.add(new_team_coordinator.user)
                print("permission")

            # # Print the permissions of the new team coordinator user for this group
            # user_permissions = new_team_coordinator.user.get_group_permissions(workspace_team_group)
            # print(f"Permissions for user {new_team_coordinator.user.username} in group '{workspace_team_group_name}': {list(user_permissions)}")
        return team
    except Exception as e:
        # Audit logging: Log team update failure
        try:
            BusinessAuditLogger.log_operation_failure(
                user=current_user,
                operation_type="team_form_update",
                error=e,
                request=None,
                team_id=str(team.team_id),
                team_title=team.title,
                organization_id=str(organization.organization_id),
                organization_title=organization.title,
                attempted_coordinator_change=f"{previous_team_coordinator} -> {form.cleaned_data.get('team_coordinator', 'Unknown')}",
            )
        except Exception as audit_error:
            logger.error(
                f"Audit logging failed for team update failure: {audit_error}",
                exc_info=True,
            )
        raise TeamUpdateError(f"Failed to update team: {str(e)}")


def remove_team_member(team_member: TeamMember, team: Team, user=None) -> None:
    """
    Removes a team member.
    """
    try:
        # Set audit user for signal handler to capture removal metadata
        current_user = user if user else team_member.organization_member.user
        team_member._audit_user = current_user

        team_member.delete()
        team.team_coordinator = None
        team.save()
        update_team_coordinator_group(team, team_member.organization_member, None)

    except Exception as e:
        raise TeamMemberDeletionError(f"Failed to remove team member: {str(e)}")


# def delete_team(team: Team) -> Team:
#     """
#     Deletes a team.
#     """
#     try:
#         team.delete()
#     except Exception as e:
#         raise TeamDeletionError(f"Failed to delete team: {str(e)}")
