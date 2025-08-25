from typing import Tuple, Optional
from .models import Invitation
from apps.organizations.models import OrganizationMember, Organization

from django.contrib.auth import get_user_model


def is_user_organization_member(user, organization: Organization) -> bool:
    """Check if the user is a member of the organization"""
    return OrganizationMember.objects.filter(
        user=user, organization=organization
    ).exists()


def get_organization_member_by_user_and_organization(
    user, organization: Organization
) -> OrganizationMember:
    """Get organization member by user and organization"""
    return OrganizationMember.objects.get(user=user, organization=organization)


def get_invitations_for_organization(organization_id: int):
    """Get all invitations for a specific organization"""
    return Invitation.objects.filter(organization=organization_id).order_by("-created_at")


def get_invitation_by_token(
    invitation_token: str,
) -> Tuple[bool, str, Optional[Invitation]]:
    """Verify invitation token and return invitation object if valid"""
    try:
        invitation = Invitation.objects.get(token=invitation_token)
        return True, "Invitation verified successfully", invitation
    except Invitation.DoesNotExist:
        return False, "Invalid Invitation Link", None


def is_user_invitation_recipient(user, invitation: Invitation) -> Tuple[bool, str]:
    """Check if the user is the intended recipient of the invitation"""
    if invitation.email != user.email:
        return False, "Invitation link is not for this user account"
    return True, ""


def is_user_in_organization(user, invitation: Invitation) -> Tuple[bool, str]:
    """Check if user is not already in the organization"""
    user_exists_in_org = OrganizationMember.objects.filter(
        user=user, organization=invitation.organization
    ).exists()

    if user_exists_in_org:
        return True, "You have already joined this organization"
    return False, ""


def is_invitation_valid(invitation: Invitation) -> Tuple[bool, str]:
    """Check if the invitation is still valid"""
    if not invitation.is_valid:
        return False, "Invitation link is expired"
    return True, ""


def invitation_exists(pk: str) -> bool:
    """Check if an invitation with the given pk exists."""
    return Invitation.objects.filter(pk=pk).exists()


def get_invitation_by_id(pk: int) -> Invitation:
    """Get invitation by id"""
    try:
        return Invitation.objects.get(pk=pk)
    except Invitation.DoesNotExist:
        raise Invitation.DoesNotExist("Invitation not found")


User = get_user_model()


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email (case-insensitive)"""
    return User.objects.filter(email__iexact=email).first()
