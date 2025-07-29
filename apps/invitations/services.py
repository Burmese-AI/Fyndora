from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Invitation
from apps.organizations.models import OrganizationMember, Organization
from .selectors import (
    get_invitation_by_token,
    is_user_invitation_recipient,
    is_invitation_valid,
    is_user_in_organization,
)

User = get_user_model()


@transaction.atomic
def create_invitation(
    email: str, expired_at, organization: Organization, invited_by: OrganizationMember
):
    """Create a new invitation for an organization"""
    invitation = Invitation.objects.create(
        email=email,
        expired_at=expired_at,
        organization=organization,
        invited_by=invited_by,
    )
    return invitation


@transaction.atomic
def accept_invitation(user: User, invitation: Invitation):
    """Accept an invitation and add user to organization"""
    # Check if invitation is already used
    if invitation.is_used:
        return False
    
    # Check if invitation is expired or not valid
    if not invitation.is_valid:
        return False
    
    # Check if user email matches invitation email
    if invitation.email != user.email:
        return False
    
    # Check if user is already a member
    if OrganizationMember.objects.filter(user=user, organization=invitation.organization).exists():
        return False
    
    # Add user to organization
    OrganizationMember.objects.create(user=user, organization=invitation.organization)

    # Update invitation status
    invitation.is_used = True
    invitation.is_active = False
    invitation.save()

    return invitation


def verify_invitation_for_acceptance(user: User, invitation_token: str):
    """Verify all conditions for accepting an invitation."""
    is_verified, message, invitation = get_invitation_by_token(invitation_token)
    if not is_verified:
        return False, message, None

    is_recipient, message = is_user_invitation_recipient(user, invitation)
    if not is_recipient:
        return False, message, None

    is_user_in_org, message = is_user_in_organization(user, invitation)
    if is_user_in_org:
        return False, message, None

    is_valid, message = is_invitation_valid(invitation)
    if not is_valid:
        return False, message, None

    return True, "", invitation


def deactivate_all_unused_active_invitations(email: str, organization: Organization):
    """Deactivate all unused and active invitations for a given email and organization."""
    return Invitation.objects.filter(
        email=email,
        organization=organization,
        is_used=False,
        is_active=True,
    ).update(is_active=False)
