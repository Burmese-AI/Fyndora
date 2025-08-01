"""
Unit tests for invitation selectors.
"""

import pytest
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.invitations import services, selectors
from tests.factories import (
    InvitationFactory,
    ExpiredInvitationFactory,
    UsedInvitationFactory,
    InactiveInvitationFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestInvitationSelectors(TestCase):
    """Test cases for invitation selectors."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.non_member_user = CustomUserFactory()

    def test_is_user_organization_member_true(self):
        """Test is_user_organization_member returns True for organization member."""
        result = selectors.is_user_organization_member(
            user=self.user, organization=self.organization
        )
        self.assertTrue(result)

    def test_is_user_organization_member_false(self):
        """Test is_user_organization_member returns False for non-member."""
        result = selectors.is_user_organization_member(
            user=self.non_member_user, organization=self.organization
        )
        self.assertFalse(result)

    def test_get_organization_member_by_user_and_organization(self):
        """Test get_organization_member_by_user_and_organization returns correct member."""
        # Create additional member
        user = CustomUserFactory()
        created_member = OrganizationMemberFactory(
            organization=self.organization, user=user
        )

        # Call the selector function
        retrieved_member = selectors.get_organization_member_by_user_and_organization(
            user=created_member.user, organization=created_member.organization
        )

        # Verify the correct member is returned
        self.assertEqual(
            retrieved_member.organization_member_id,
            created_member.organization_member_id,
        )
        self.assertEqual(retrieved_member.user, created_member.user)
        self.assertEqual(retrieved_member.organization, created_member.organization)

    def test_get_invitations_for_organization(self):
        """Test get_invitations_for_organization returns correct invitations."""
        # Create invitations for this organization
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        # Create invitation for different organization
        other_org = OrganizationFactory()
        other_member = OrganizationMemberFactory(organization=other_org)
        InvitationFactory(organization=other_org, invited_by=other_member)

        invitations = selectors.get_invitations_for_organization(
            self.organization.organization_id
        )

        self.assertEqual(invitations.count(), 2)
        self.assertIn(invitation1, invitations)
        self.assertIn(invitation2, invitations)

    def test_get_invitation_by_token_exists(self):
        """Test get_invitation_by_token returns success tuple when token exists."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        success, message, result_invitation = selectors.get_invitation_by_token(
            invitation.token
        )

        self.assertTrue(success)
        self.assertEqual(message, "Invitation verified successfully")
        self.assertEqual(result_invitation, invitation)

    def test_get_invitation_by_token_not_exists(self):
        """Test get_invitation_by_token returns failure tuple when token doesn't exist."""
        non_existent_uuid = str(uuid.uuid4())
        success, message, result_invitation = selectors.get_invitation_by_token(
            non_existent_uuid
        )

        self.assertFalse(success)
        self.assertEqual(message, "Invalid Invitation Link")
        self.assertIsNone(result_invitation)

    def test_is_user_invitation_recipient_correct_email(self):
        """Test is_user_invitation_recipient returns True for correct email."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email=self.user.email,
        )

        is_recipient, message = selectors.is_user_invitation_recipient(
            self.user, invitation
        )

        self.assertTrue(is_recipient)
        self.assertEqual(message, "")

    def test_is_user_invitation_recipient_wrong_email(self):
        """Test is_user_invitation_recipient returns False for wrong email."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="different@example.com",
        )

        is_recipient, message = selectors.is_user_invitation_recipient(
            self.user, invitation
        )

        self.assertFalse(is_recipient)
        self.assertEqual(message, "Invitation link is not for this user account")

    def test_is_user_in_organization_true(self):
        """Test is_user_in_organization returns True when user is already in organization."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        is_in_org, message = selectors.is_user_in_organization(self.user, invitation)

        self.assertTrue(is_in_org)
        self.assertEqual(message, "You have already joined this organization")

    def test_is_user_in_organization_false(self):
        """Test is_user_in_organization returns False when user is not in organization."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        is_in_org, message = selectors.is_user_in_organization(
            self.non_member_user, invitation
        )

        self.assertFalse(is_in_org)
        self.assertEqual(message, "")

    def test_is_invitation_valid_true(self):
        """Test is_invitation_valid returns True for valid invitation."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        is_valid, message = selectors.is_invitation_valid(invitation)

        self.assertTrue(is_valid)
        self.assertEqual(message, "")

    def test_is_invitation_valid_false(self):
        """Test is_invitation_valid returns False for invalid invitation."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        is_valid, message = selectors.is_invitation_valid(invitation)

        self.assertFalse(is_valid)
        self.assertEqual(message, "Invitation link is expired")

    def test_invitation_exists_true(self):
        """Test invitation_exists returns True when invitation exists."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        exists = selectors.invitation_exists(str(invitation.pk))

        self.assertTrue(exists)

    def test_invitation_exists_false(self):
        """Test invitation_exists returns False when invitation doesn't exist."""
        non_existent_uuid = str(uuid.uuid4())
        exists = selectors.invitation_exists(non_existent_uuid)

        self.assertFalse(exists)

    def test_get_user_by_email_exists(self):
        """Test get_user_by_email returns user when email exists."""
        user = selectors.get_user_by_email(self.user.email)

        self.assertEqual(user, self.user)

    def test_get_user_by_email_case_insensitive(self):
        """Test get_user_by_email is case insensitive."""
        user = selectors.get_user_by_email(self.user.email.upper())

        self.assertEqual(user, self.user)

    def test_get_user_by_email_not_exists(self):
        """Test get_user_by_email returns None when email doesn't exist."""
        user = selectors.get_user_by_email("nonexistent@example.com")

        self.assertIsNone(user)

    def test_validate_invitation_valid(self):
        """Test validate_invitation returns True for valid invitation."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email=self.non_member_user.email,
        )

        result, message, invitation = services.verify_invitation_for_acceptance(
            invitation_token=invitation.token, user=self.non_member_user
        )

        self.assertTrue(result)

    def test_validate_invitation_wrong_email(self):
        """Test validate_invitation returns False for wrong email."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

        result, message, invitation = services.verify_invitation_for_acceptance(
            invitation_token=invitation.token, user=self.user
        )

        self.assertFalse(result)

    def test_validate_invitation_expired(self):
        """Test validate_invitation returns False for expired invitation."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

        result, message, invitation = services.verify_invitation_for_acceptance(
            invitation_token=invitation.token, user=self.user
        )

        self.assertFalse(result)

    def test_validate_invitation_used(self):
        """Test validate_invitation returns False for used invitation."""
        invitation = UsedInvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

        result, message, invitation = services.verify_invitation_for_acceptance(
            invitation_token=invitation.token, user=self.user
        )

        self.assertFalse(result)

    def test_validate_invitation_inactive(self):
        """Test validate_invitation returns False for inactive invitation."""
        invitation = InactiveInvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

        result, message, invitation = services.verify_invitation_for_acceptance(
            invitation_token=invitation.token, user=self.user
        )

        self.assertFalse(result)

    def test_validate_invitation_user_already_member(self):
        """Test validate_invitation returns False if user is already a member."""
        # Create a user who is already a member
        existing_user = CustomUserFactory(email="test@example.com")
        OrganizationMemberFactory(organization=self.organization, user=existing_user)

        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

        result, message, invitation = services.verify_invitation_for_acceptance(
            invitation_token=invitation.token, user=self.user
        )

        self.assertFalse(result)

    def test_validate_invitation_case_insensitive_email(self):
        """Test validate_invitation with case mismatch in email."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email=self.non_member_user.email.upper(),
        )

        result, message, invitation = services.verify_invitation_for_acceptance(
            invitation_token=invitation.token, user=self.non_member_user
        )

        # Should fail because selector uses exact string comparison, not case-insensitive
        self.assertFalse(result)
        self.assertEqual(message, "Invitation link is not for this user account")

    def test_get_invitations_for_organization_ordering(self):
        """Test that organization invitations are ordered by created_at descending."""
        # Create invitations with slight time differences
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        invitations = selectors.get_invitations_for_organization(
            self.organization.organization_id
        )

        # The most recently created should be first
        self.assertEqual(invitations.first(), invitation2)
        self.assertEqual(invitations.last(), invitation1)
