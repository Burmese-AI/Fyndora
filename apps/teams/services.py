from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from guardian.shortcuts import assign_perm

from apps.auditlog.services import audit_create
from apps.core.roles import get_permissions_for_role
from apps.organizations.models import OrganizationMember

from .models import Team, TeamMember

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

  
def create_team_from_form(form, organization):
    team = form.save(commit=False)
    team.organization = organization
    team.save()
    return team
