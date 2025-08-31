"""
Unit tests for invitation models.
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.db import IntegrityError
from django.db.models.signals import post_save
from apps.invitations.signals import send_invitation_email

from apps.invitations.models import Invitation
from tests.factories import (
    InvitationFactory,
    ExpiredInvitationFactory,
    UsedInvitationFactory,
    InactiveInvitationFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)


@pytest.mark.unit
class TestInvitationModel(TestCase):
    """Test cases for the Invitation model."""

    def setUp(self):
        """Set up test data."""
        # Disable the post_save signal for invitations to prevent email sending
        post_save.disconnect(send_invitation_email, sender=Invitation)

        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.organization_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.future_date = timezone.now() + timedelta(days=7)

    def tearDown(self):
        """Clean up after tests."""
        # Reconnect the signal after tests
        post_save.connect(send_invitation_email, sender=Invitation)

    def test_invitation_creation(self):
        """Test creating a new invitation."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            email="test@example.com",
        )

        assert invitation.invitation_id is not None
        assert invitation.token is not None
        assert invitation.organization == self.organization
        assert invitation.invited_by == self.organization_member
        assert invitation.email == "test@example.com"
        assert not invitation.is_used
        assert invitation.is_active
        assert invitation.expired_at is not None

    def test_invitation_str_representation(self):
        """Test the string representation of an invitation."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            email="test@example.com",
        )

        expected_str = f"{invitation.pk} - {self.organization.title} - test@example.com - {invitation.token} - True"
        assert str(invitation) == expected_str

    def test_invitation_meta_ordering(self):
        """Test that invitations are ordered by created_at descending."""
        # Create invitations with slight time differences
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        invitations = Invitation.objects.all()
        # The most recently created should be first
        assert invitations.first() == invitation2
        assert invitations.last() == invitation1

    def test_invitation_base_model_fields(self):
        """Test that base model fields are present and working."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        # Check base model fields
        assert invitation.created_at is not None
        assert invitation.updated_at is not None

        # Test that updated_at changes when saving
        old_updated_at = invitation.updated_at
        invitation.email = "newemail@example.com"
        invitation.save()
        invitation.refresh_from_db()
        assert invitation.updated_at > old_updated_at

    def test_invitation_uuid_fields(self):
        """Test that UUID fields are properly generated and unique."""
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        # Check that UUIDs are generated
        assert invitation1.invitation_id is not None
        assert invitation1.token is not None
        assert invitation2.invitation_id is not None
        assert invitation2.token is not None

        # Check that UUIDs are unique
        assert invitation1.invitation_id != invitation2.invitation_id
        assert invitation1.token != invitation2.token

        # Check that UUIDs are editable (Django allows this)
        # But they should be unique and properly formatted
        old_invitation_id = invitation1.invitation_id
        old_token = invitation1.token

        # We can change them, but they should remain UUIDs
        invitation1.invitation_id = invitation1.invitation_id  # Same value
        invitation1.token = invitation1.token  # Same value

        assert invitation1.invitation_id == old_invitation_id
        assert invitation1.token == old_token

    def test_invitation_relationships(self):
        """Test invitation relationships with other models."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        # Test organization relationship
        assert invitation.organization == self.organization
        assert invitation in self.organization.invitations.all()

        # Test invited_by relationship
        assert invitation.invited_by == self.organization_member
        assert invitation in self.organization_member.invitations_sent.all()

    def test_invitation_email_field(self):
        """Test invitation email field validation and constraints."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        # Test email field
        assert invitation.email is not None
        assert len(invitation.email) <= 255  # max_length constraint

        # Test that email can be updated
        new_email = "newemail@example.com"
        invitation.email = new_email
        invitation.save()
        invitation.refresh_from_db()
        assert invitation.email == new_email

    def test_invitation_boolean_fields(self):
        """Test invitation boolean fields and their defaults."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        # Test default values
        assert not invitation.is_used
        assert invitation.is_active

        # Test that boolean fields can be updated
        invitation.is_used = True
        invitation.is_active = False
        invitation.save()
        invitation.refresh_from_db()
        assert invitation.is_used
        assert not invitation.is_active

    def test_invitation_expired_at_field(self):
        """Test invitation expired_at field."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        # Test that expired_at is set
        assert invitation.expired_at is not None
        assert isinstance(invitation.expired_at, timezone.datetime)

        # Test that expired_at can be updated
        new_expiry = timezone.now() + timedelta(days=14)
        invitation.expired_at = new_expiry
        invitation.save()
        invitation.refresh_from_db()
        assert invitation.expired_at == new_expiry

    def test_invitation_is_expired_property(self):
        """Test the is_expired property."""
        # Test future date (not expired)
        future_date = timezone.now() + timedelta(days=7)
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            expired_at=future_date,
        )
        assert not invitation.is_expired

        # Test past date (expired)
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        assert invitation.is_expired

        # Test current time (should be considered expired)
        current_time = timezone.now()
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            expired_at=current_time,
        )
        assert invitation.is_expired

    def test_invitation_is_valid_property(self):
        """Test the is_valid property."""
        # Test valid invitation
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        assert invitation.is_valid

        # Test expired invitation
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        assert not invitation.is_valid

        # Test used invitation
        invitation = UsedInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        assert not invitation.is_valid

        # Test inactive invitation
        invitation = InactiveInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        assert not invitation.is_valid

        # Test combination of invalid states
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation.is_used = True
        invitation.is_active = False
        invitation.save()
        assert not invitation.is_valid

    def test_invitation_get_acceptance_url(self):
        """Test the get_acceptance_url method."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        expected_url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        assert invitation.get_acceptance_url() == expected_url

    def test_invitation_cascade_delete_organization(self):
        """Test that invitations are deleted when organization is deleted."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation_id = invitation.invitation_id

        # Hard delete the organization to trigger CASCADE
        self.organization.hard_delete()

        # Invitation should be deleted due to CASCADE
        try:
            Invitation.objects.get(invitation_id=invitation_id)
            # If we get here, the invitation still exists
            assert False, "Invitation should have been deleted"
        except Invitation.DoesNotExist:
            # This is what we expect
            pass

    def test_invitation_set_null_invited_by(self):
        """Test that invitation.invited_by is set to null when OrganizationMember is deleted."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation_id = invitation.invitation_id

        # Hard delete the invited_by member to trigger SET_NULL
        self.organization_member.hard_delete()

        # Invitation should still exist but invited_by should be null
        invitation.refresh_from_db()
        assert invitation.invited_by is None
        assert invitation.invitation_id == invitation_id

    def test_invitation_token_uniqueness(self):
        """Test that invitation tokens are unique."""
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        assert invitation1.token != invitation2.token

        # Test that we can't create an invitation with a duplicate token
        invitation3 = InvitationFactory.build(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation3.token = invitation1.token

        with pytest.raises(IntegrityError):
            invitation3.save()

    def test_invitation_id_uniqueness(self):
        """Test that invitation IDs are unique."""
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )

        assert invitation1.invitation_id != invitation2.invitation_id

    def test_invitation_without_invited_by(self):
        """Test that invitation can be created without invited_by (null=True)."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=None,
        )

        assert invitation.invited_by is None
        assert invitation.organization == self.organization
        assert invitation.is_valid  # Should still be valid if not expired

    def test_invitation_edge_cases(self):
        """Test invitation edge cases and boundary conditions."""
        # Test with very long email
        long_email = "a" * 250 + "@example.com"
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            email=long_email,
        )
        assert invitation.email == long_email

        # Test with very short expiry time
        short_expiry = timezone.now() + timedelta(seconds=1)
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            expired_at=short_expiry,
        )
        assert invitation.expired_at == short_expiry
        assert not invitation.is_expired  # Should not be expired yet

    def test_invitation_property_combinations(self):
        """Test various combinations of invitation properties."""
        # Test active but expired invitation
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation.is_active = True
        invitation.is_used = False
        invitation.save()
        assert not invitation.is_valid  # Expired should make it invalid

        # Test inactive but not expired invitation
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation.is_active = False
        invitation.is_used = False
        invitation.save()
        assert not invitation.is_valid  # Inactive should make it invalid

        # Test used but not expired invitation
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation.is_used = True
        invitation.is_active = True
        invitation.save()
        assert not invitation.is_valid  # Used should make it invalid
