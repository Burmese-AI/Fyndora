from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from guardian.shortcuts import assign_perm
from apps.auditlog.services import audit_create
from apps.core.roles import get_permissions_for_role
from apps.organizations.models import OrganizationMember
from apps.teams.exceptions import TeamMemberUpdateError

from .models import Team, TeamMember
from apps.teams.exceptions import TeamCreationError
from apps.core.utils import model_update


def create_team_from_form(form, organization):
    try:
        team = form.save(commit=False)
        team.organization = organization
        team.save()
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


def create_team_member_from_form(form, team, organization):
    team_member = form.save(commit=False)
    team_member.team = team
    team_member.organization = organization
    team_member.save()
    return team_member


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
