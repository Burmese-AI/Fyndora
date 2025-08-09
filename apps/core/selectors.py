from typing import Optional
from django.contrib.auth import get_user_model
from apps.organizations.models import OrganizationMember, Organization
from apps.workspaces.models import Workspace, WorkspaceTeam
from apps.remittance.models import Remittance

User = get_user_model()


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email"""
    return User.objects.filter(email=email).first()


def get_org_members_without_owner(organization):
    """
    Return organization members without the owner.
    """
    try:
        return OrganizationMember.objects.filter(organization=organization).exclude(
            user=organization.owner.user
        )
    except Exception as e:
        print(f"Error in get_org_members_without_owner: {str(e)}")
        return None


def get_organization_by_id(organization_id):
    """
    Return organization by id.
    """
    try:
        return Organization.objects.get(pk=organization_id)
    except Exception as e:
        print(f"Error in get_organization_by_id: {str(e)}")
        return None


def get_workspaces_under_organization(organization_id):
    """
    Return workspaces under organization.
    """
    try:
        return Workspace.objects.filter(organization=organization_id)
    except Exception as e:
        print(f"Error in get_workspaces_under_organization: {str(e)}")
        return None


def get_workspace_teams_under_organization(organization_id, workspace_id=None):
    """
    Return workspace teams under organization.
    """
    try:
        workspaces = get_workspaces_under_organization(organization_id)
        return WorkspaceTeam.objects.filter(workspace__in=workspaces)
    except Exception as e:
        print(f"Error in get_workspace_teams_under_organization: {str(e)}")
        return None


def get_remiitances_under_organization(organization_id, workspace_id=None):
    """
    Return remittances under organization.
    """
    try:
        if workspace_id:
            # Filter workspace teams by specific workspace
            workspace_teams = WorkspaceTeam.objects.filter(
                workspace__organization=organization_id,
                workspace=workspace_id
            )
        else:
            # Get all workspace teams under organization
            workspace_teams = WorkspaceTeam.objects.filter(
                workspace__organization=organization_id
            )
        
        remittances = Remittance.objects.filter(workspace_team__in=workspace_teams)
        for remittance in remittances:
            remittance.remaining_amount = remittance.due_amount - remittance.paid_amount
        return remittances
    except Exception as e:
        print(f"Error in get_remiitances_under_organization: {str(e)}")
        return None
