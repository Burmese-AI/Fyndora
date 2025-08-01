"""
Unit tests for invitation models.
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.invitations.models import Invitation
from tests.factories import (
    InvitationFactory,
    ExpiredInvitationFactory,
    UsedInvitationFactory,
    InactiveInvitationFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
)


@pytest.mark.unit
class TestInvitationModel(TestCase):
    """Test cases for the Invitation model."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.invited_by = OrganizationMemberFactory(organization=self.organization)

    def test_invitation_creation(self):
        """Test creating a new invitation."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.invited_by,
            email="test@example.com",
        )

        self.assertIsNotNone(invitation.invitation_id)
        self.assertIsNotNone(invitation.token)
        self.assertEqual(invitation.organization, self.organization)
        self.assertEqual(invitation.invited_by, self.invited_by)
        self.assertEqual(invitation.email, "test@example.com")
        self.assertFalse(invitation.is_used)
        self.assertTrue(invitation.is_active)
        self.assertIsNotNone(invitation.expired_at)

    def test_invitation_str_representation(self):
        """Test the string representation of an invitation."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.invited_by,
            email="test@example.com",
        )

        expected_str = f"{invitation.pk} - {self.organization.title} - test@example.com - {invitation.token} - True"
        self.assertEqual(str(invitation), expected_str)

    def test_is_expired_property_false(self):
        """Test is_expired property returns False for valid invitation."""
        future_date = timezone.now() + timedelta(days=7)
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.invited_by,
            expired_at=future_date,
        )

        self.assertFalse(invitation.is_expired)

    def test_is_expired_property_true(self):
        """Test is_expired property returns True for expired invitation."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        self.assertTrue(invitation.is_expired)

    def test_is_valid_property_true(self):
        """Test is_valid property returns True for valid invitation."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        self.assertTrue(invitation.is_valid)

    def test_is_valid_property_false_expired(self):
        """Test is_valid property returns False for expired invitation."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        self.assertFalse(invitation.is_valid)

    def test_is_valid_property_false_used(self):
        """Test is_valid property returns False for used invitation."""
        invitation = UsedInvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        self.assertFalse(invitation.is_valid)

    def test_is_valid_property_false_inactive(self):
        """Test is_valid property returns False for inactive invitation."""
        invitation = InactiveInvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        self.assertFalse(invitation.is_valid)

    def test_invitation_token_uniqueness(self):
        """Test that invitation tokens are unique."""
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        self.assertNotEqual(invitation1.token, invitation2.token)

    def test_invitation_id_uniqueness(self):
        """Test that invitation IDs are unique."""
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        self.assertNotEqual(invitation1.invitation_id, invitation2.invitation_id)

    def test_invitation_ordering(self):
        """Test that invitations are ordered by created_at descending."""
        # Create invitations with slight time differences
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )

        invitations = Invitation.objects.all()
        # The most recently created should be first
        self.assertEqual(invitations.first(), invitation2)
        self.assertEqual(invitations.last(), invitation1)

    def test_invitation_cascade_delete_organization(self):
        """Test that invitations are deleted when organization is deleted."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )
        invitation_id = invitation.invitation_id

        # Delete the organization
        self.organization.delete()

        # Invitation should be deleted
        with self.assertRaises(Invitation.DoesNotExist):
            Invitation.objects.get(invitation_id=invitation_id)

    def test_invitation_set_null_invited_by(self):
        """Test that invitation.invited_by is set to null when OrganizationMember is deleted."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.invited_by
        )
        invitation_id = invitation.invitation_id

        # Delete the invited_by member
        self.invited_by.delete()

        # Invitation should still exist but invited_by should be null
        invitation.refresh_from_db()
        self.assertIsNone(invitation.invited_by)
        self.assertEqual(invitation.invitation_id, invitation_id)
