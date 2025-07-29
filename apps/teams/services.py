from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from guardian.shortcuts import assign_perm
from apps.auditlog.services import audit_create
from apps.core.roles import get_permissions_for_role
from apps.organizations.models import OrganizationMember
from apps.teams.exceptions import (
    TeamCreationError,
    TeamMemberUpdateError,
    TeamUpdateError,
    TeamMemberCreationError,
    TeamMemberDeletionError,
)
from apps.teams.permissions import assign_team_permissions

from .models import Team, TeamMember
from apps.core.utils import model_update
from apps.teams.permissions import update_team_coordinator_group
from apps.teams.selectors import get_team_members_by_team_id


def create_team_from_form(form, organization, orgMember):
    try:
        team = form.save(commit=False)
        team.organization = organization
        team.created_by = orgMember
        team.save()
        print(team.team_coordinator)
        
        if team.team_coordinator:

            team_member = TeamMember.objects.create(
            team=team,
            organization_member=team.team_coordinator,
            role="team_coordinator",
        )

        assign_team_permissions(team)
        return team
    except Exception as e:
        raise TeamCreationError(f"An error occurred while creating team: {str(e)}")


User = get_user_model()


@transaction.atomic
def team_member_add(
    *, added_by: User, org_member: OrganizationMember, team: Team, role: str
) -> TeamMember:
    """
    Adds an organization member to a team with a specific role and assigns all the
    necessary permissions for that role using Django groups.
    """
    try:
        role = role.upper()

        team_member, _ = TeamMember.objects.update_or_create(
            organization_member=org_member, team=team, defaults={"role": role}
        )

        workspace = team.workspace

        group_name = f"{workspace.workspace_id}_{team.team_id}_{role}"
        group, created = Group.objects.get_or_create(name=group_name)

        if created:
            permissions = get_permissions_for_role(role)
            for perm in permissions:
                assign_perm(perm, group, workspace)

        group.user_set.add(org_member.user)

        audit_create(
            user=added_by,
            action_type="team_member_added",
            target_entity=team_member,
            metadata={"role": role, "team": team.title},
        )

        return team_member
    except Exception as e:
        raise TeamMemberCreationError(
            f"An error occurred while adding team member: {str(e)}"
        )


def create_team_member_from_form(form, team, organization):
    try:
        team_member = form.save(commit=False)
        team_member.team = team
        team_member.organization = organization
        team_member.save()
        return team_member
    except Exception as e:
        raise TeamMemberCreationError(
            f"An error occurred while creating team member: {str(e)}"
        )


@transaction.atomic
def update_team_member_role(*, form, team_member) -> TeamMember:
    """
    Updates a team member role from a form.
    """
    try:
        team_member = model_update(team_member, {"role": form.cleaned_data["role"]})
        return team_member
    except Exception as e:
        raise TeamMemberUpdateError(f"Failed to update team member: {str(e)}")


def update_team_from_form(form, team, organization, previous_team_coordinator) -> Team:
    """
    Updates a team from a form.
    """
    try:
        team = model_update(team, form.cleaned_data)
        new_team_coordinator = form.cleaned_data.get("team_coordinator")
        update_team_coordinator_group(
            team, previous_team_coordinator, new_team_coordinator
        )
        return team
    except Exception as e:
        raise TeamUpdateError(f"Failed to update team: {str(e)}")


def remove_team_member(team_member: TeamMember) -> None:
    """
    Removes a team member.
    """
    try:
        team_member.delete()
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
