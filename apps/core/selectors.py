from django.contrib.auth import get_user_model
from apps.organizations.models import OrganizationMember, Organization
from apps.workspaces.models import Workspace, WorkspaceTeam

User = get_user_model()


def get_user_by_email(email: str):
    """Get user by email"""
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        # this is the error case
        return User.objects.filter(email=email).first()
    except Exception as e:
        return None


def get_org_members_without_owner(organization):
    """
    Return organization members without the owner.
    """
    try:
        qs = OrganizationMember.objects.filter(organization=organization)
        # If the organization has an owner, exclude them; otherwise return all members
        # actually every org has its owner ... i just added this for testing edge cases
        owner = getattr(organization, "owner", None)
        if owner and getattr(owner, "user", None):
            return qs.exclude(user=owner.user)
        return qs
    except Exception as e:
        return None


def get_organization_by_id(organization_id):
    """
    Return organization by id.
    """
    try:
        return Organization.objects.get(pk=organization_id)
    except Exception as e:
        return None


def get_workspaces_under_organization(organization_id):
    """
    Return workspaces under organization.
    """
    try:
        return Workspace.objects.filter(organization=organization_id)
    except Exception as e:
        return None


def get_workspace_teams_under_organization(organization_id, workspace_id=None):
    """
    Return workspace teams under organization.
    """
    try:
        workspaces = get_workspaces_under_organization(organization_id)
        return WorkspaceTeam.objects.filter(workspace__in=workspaces)
    except Exception as e:
        return None
