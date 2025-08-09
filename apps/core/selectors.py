from typing import Optional
from django.contrib.auth import get_user_model
from apps.organizations.models import OrganizationMember, Organization

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