from apps.organizations.models import OrganizationMember
from apps.workspaces.models import Workspace

def get_user_org_memberships(user):
    return OrganizationMember.objects.filter(user=user)

def get_user_workspaces(user):
    return Workspace.objects.filter(organization_id__in=get_user_org_memberships(user))