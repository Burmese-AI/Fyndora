"""Unit tests for invitation services."""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.invitations import services
from apps.invitations.models import Invitation
from tests.factories import (
    CustomUserFactory,
    ExpiredInvitationFactory,
    InvitationFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    UsedInvitationFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestInvitationServices(TestCase):
    """Test cases for invitation services."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.non_member_user = CustomUserFactory()

    def test_create_invitation_success(self):
        """Test successful invitation creation."""
        email = "test@example.com"
        expired_at = timezone.now() + timedelta(days=7)

        invitation = services.create_invitation(
            organization=self.organization,
            invited_by=self.member,
            email=email,
            expired_at=expired_at,
        )

        self.assertIsInstance(invitation, Invitation)
        self.assertEqual(invitation.organization, self.organization)
        self.assertEqual(invitation.invited_by, self.member)
        self.assertEqual(invitation.email, email)
        self.assertEqual(invitation.expired_at, expired_at)
        self.assertTrue(invitation.is_active)
        self.assertFalse(invitation.is_used)
        self.assertIsNotNone(invitation.token)
        self.assertIsNotNone(invitation.invitation_id)

    def test_create_invitation_default_expiration(self):
        """Test invitation creation with default expiration."""
        email = "test@example.com"
        expected_expiration = timezone.now() + timedelta(days=7)

        invitation = services.create_invitation(
            email=email,
            expired_at=expected_expiration,
            organization=self.organization,
            invited_by=self.member,
        )

        # Should have the specified expiration
        self.assertEqual(invitation.expired_at, expected_expiration)

    def test_create_invitation_email_task_failure(self):
        """Test invitation creation when email task fails."""
        email = "test@example.com"
        expired_at = timezone.now() + timedelta(days=7)

        # Should still create invitation even if email fails
        invitation = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.member,
        )

        self.assertIsInstance(invitation, Invitation)

    def test_accept_invitation_success(self):
        """Test successful invitation acceptance."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")

        result = services.accept_invitation(invitation=invitation, user=accepting_user)

        self.assertTrue(result)

        # Verify invitation is marked as used
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)

        # Verify user is added to organization
        self.assertTrue(self.organization.members.filter(user=accepting_user).exists())

    def test_accept_invitation_invalid(self):
        """Test accepting an invalid invitation."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")

        result = services.accept_invitation(invitation=invitation, user=accepting_user)

        self.assertFalse(result)

        # Verify invitation is not marked as used
        invitation.refresh_from_db()
        self.assertFalse(invitation.is_used)

        # Verify user is not added to organization
        self.assertFalse(self.organization.members.filter(user=accepting_user).exists())

    def test_accept_invitation_wrong_email(self):
        """Test accepting invitation with wrong email."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="wrong@example.com")

        result = services.accept_invitation(invitation=invitation, user=accepting_user)

        self.assertFalse(result)

    def test_accept_invitation_already_member(self):
        """Test accepting invitation when user is already a member."""
        accepting_user = CustomUserFactory(email="test@example.com")
        # Make user already a member
        OrganizationMemberFactory(organization=self.organization, user=accepting_user)

        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

        result = services.accept_invitation(invitation=invitation, user=accepting_user)

        self.assertFalse(result)

    def test_verify_invitation_valid(self):
        """Test verification with valid invitation."""
        # Create invitation for the user's email
        invitation = InvitationFactory(
            organization=self.organization,
            email=self.non_member_user.email,  # Use non-member user to avoid membership conflict
        )

        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            self.non_member_user, str(invitation.token)
        )

        self.assertTrue(result)
        self.assertEqual(message, "")
        self.assertEqual(invitation_obj, invitation)

    def test_verify_invitation_invalid_token(self):
        """Test verification with invalid token."""
        invalid_token = str(uuid.uuid4())  # Valid UUID format but non-existent

        result, message, invitation = services.verify_invitation_for_acceptance(
            self.user, invalid_token
        )

        self.assertFalse(result)
        self.assertIsNotNone(message)
        self.assertIsNone(invitation)

    def test_verify_invitation_invalid_email(self):
        """Test verification with invalid email."""
        # Create invitation for a different email
        invitation = InvitationFactory(
            organization=self.organization, email="different@example.com"
        )

        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            self.user, str(invitation.token)
        )

        self.assertFalse(result)
        self.assertIsNotNone(message)
        self.assertIsNone(invitation_obj)

    def test_deactivate_unused_invitations(self):
        """Test deactivating unused invitations for an email."""
        email = "test@example.com"

        # Create multiple invitations for the same email
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.member, email=email
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.member, email=email
        )

        # Create invitation for different email (should not be affected)
        other_invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="other@example.com",
        )

        # Create already used invitation (should not be affected)
        used_invitation = UsedInvitationFactory(
            organization=self.organization, invited_by=self.member, email=email
        )

        count = services.deactivate_all_unused_active_invitations(
            organization=self.organization, email=email
        )

        self.assertEqual(count, 2)

        # Verify invitations are deactivated
        invitation1.refresh_from_db()
        invitation2.refresh_from_db()
        self.assertFalse(invitation1.is_active)
        self.assertFalse(invitation2.is_active)

        # Verify other invitations are not affected
        other_invitation.refresh_from_db()
        used_invitation.refresh_from_db()
        self.assertTrue(other_invitation.is_active)
        self.assertFalse(used_invitation.is_active)  # Was already inactive

    def test_deactivate_unused_invitations_no_matches(self):
        """Test deactivating unused invitations when no matches exist."""
        count = services.deactivate_all_unused_active_invitations(
            organization=self.organization, email="nonexistent@example.com"
        )

        self.assertEqual(count, 0)

    def test_deactivate_unused_invitations_different_organization(self):
        """Test that deactivation only affects the specified organization."""
        email = "test@example.com"

        # Create invitation in this organization
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.member, email=email
        )

        # Create invitation in different organization
        other_org = OrganizationFactory()
        other_member = OrganizationMemberFactory(organization=other_org)
        invitation2 = InvitationFactory(
            organization=other_org, invited_by=other_member, email=email
        )

        count = services.deactivate_all_unused_active_invitations(
            organization=self.organization, email=email
        )

        self.assertEqual(count, 1)

        # Verify only the invitation in this organization is deactivated
        invitation1.refresh_from_db()
        invitation2.refresh_from_db()
        self.assertFalse(invitation1.is_active)
        self.assertTrue(invitation2.is_active)
