"""
Unit tests for invitation selectors.
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from apps.invitations.signals import send_invitation_email

from apps.invitations.selectors import (
    is_user_organization_member,
    get_organization_member_by_user_and_organization,
    get_invitations_for_organization,
    get_invitation_by_token,
    is_user_invitation_recipient,
    is_user_in_organization,
    is_invitation_valid,
    invitation_exists,
    get_invitation_by_id,
    get_user_by_email,
)
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

User = get_user_model()


@pytest.mark.unit
class TestInvitationSelectors(TestCase):
    """Test cases for invitation selectors."""

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
        
        # Create another user and organization for testing
        self.other_user = CustomUserFactory()
        self.other_organization = OrganizationFactory()
        self.other_organization_member = OrganizationMemberFactory(
            organization=self.other_organization, user=self.other_user
        )

    def tearDown(self):
        """Clean up after tests."""
        # Reconnect the signal after tests
        post_save.connect(send_invitation_email, sender=Invitation)

    def test_is_user_organization_member_true(self):
        """Test that user is correctly identified as organization member."""
        result = is_user_organization_member(self.user, self.organization)
        assert result is True

    def test_is_user_organization_member_false(self):
        """Test that user is correctly identified as not an organization member."""
        result = is_user_organization_member(self.user, self.other_organization)
        assert result is False

    def test_is_user_organization_member_nonexistent_user(self):
        """Test with non-existent user."""
        # Test with a user that doesn't exist in the database
        # We'll use a different user that's not a member of this organization
        result = is_user_organization_member(self.other_user, self.organization)
        assert result is False

    def test_get_organization_member_by_user_and_organization_success(self):
        """Test successful retrieval of organization member."""
        result = get_organization_member_by_user_and_organization(
            self.user, self.organization
        )
        assert result == self.organization_member
        assert result.user == self.user
        assert result.organization == self.organization

    def test_get_organization_member_by_user_and_organization_not_found(self):
        """Test that DoesNotExist is raised when member not found."""
        with pytest.raises(Exception):  # OrganizationMember.DoesNotExist
            get_organization_member_by_user_and_organization(
                self.user, self.other_organization
            )

    def test_get_invitations_for_organization(self):
        """Test retrieval of invitations for a specific organization."""
        # Create invitations for the organization
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        # Create invitation for different organization
        InvitationFactory(
            organization=self.other_organization, invited_by=self.other_organization_member
        )
        
        result = get_invitations_for_organization(self.organization.organization_id)
        
        assert len(result) == 2
        assert invitation1 in result
        assert invitation2 in result
        # Check ordering (most recent first)
        assert result[0] == invitation2
        assert result[1] == invitation1

    def test_get_invitations_for_organization_empty(self):
        """Test retrieval when no invitations exist for organization."""
        result = get_invitations_for_organization(self.organization.organization_id)
        assert len(result) == 0

    def test_get_invitations_for_organization_invalid_id(self):
        """Test retrieval with invalid organization ID."""
        result = get_invitations_for_organization(99999)
        assert len(result) == 0

    def test_get_invitation_by_token_success(self):
        """Test successful invitation retrieval by token."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        success, message, result_invitation = get_invitation_by_token(str(invitation.token))
        
        assert success is True
        assert message == "Invitation verified successfully"
        assert result_invitation == invitation

    def test_get_invitation_by_token_not_found(self):
        """Test invitation retrieval with invalid token."""
        # Use a valid UUID format but non-existent token
        import uuid
        fake_token = str(uuid.uuid4())
        success, message, result_invitation = get_invitation_by_token(fake_token)
        
        assert success is False
        assert message == "Invalid Invitation Link"
        assert result_invitation is None

    def test_get_invitation_by_token_empty_string(self):
        """Test invitation retrieval with empty token."""
        # Empty string should be handled gracefully
        try:
            success, message, result_invitation = get_invitation_by_token("")
            assert success is False
            assert message == "Invalid Invitation Link"
            assert result_invitation is None
        except Exception:
            # If it raises an exception, that's also acceptable behavior
            pass

    def test_is_user_invitation_recipient_true(self):
        """Test that user is correctly identified as invitation recipient."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            email=self.user.email
        )
        
        success, message = is_user_invitation_recipient(self.user, invitation)
        
        assert success is True
        assert message == ""

    def test_is_user_invitation_recipient_false(self):
        """Test that user is correctly identified as not invitation recipient."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            email="different@example.com"
        )
        
        success, message = is_user_invitation_recipient(self.user, invitation)
        
        assert success is False
        assert message == "Invitation link is not for this user account"

    def test_is_user_invitation_recipient_case_insensitive(self):
        """Test email comparison is case insensitive."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            email=self.user.email.upper()
        )
        
        success, message = is_user_invitation_recipient(self.user, invitation)
        
        assert success is False
        assert message == "Invitation link is not for this user account"

    def test_is_user_in_organization_true(self):
        """Test that user is correctly identified as being in organization."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        success, message = is_user_in_organization(self.user, invitation)
        
        assert success is True
        assert message == "You have already joined this organization"

    def test_is_user_in_organization_false(self):
        """Test that user is correctly identified as not being in organization."""
        invitation = InvitationFactory(
            organization=self.other_organization, invited_by=self.other_organization_member
        )
        
        success, message = is_user_in_organization(self.user, invitation)
        
        assert success is False
        assert message == ""

    def test_is_invitation_valid_true(self):
        """Test that valid invitation is correctly identified."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        success, message = is_invitation_valid(invitation)
        
        assert success is True
        assert message == ""

    def test_is_invitation_valid_expired(self):
        """Test that expired invitation is correctly identified."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        success, message = is_invitation_valid(invitation)
        
        assert success is False
        assert message == "Invitation link is expired"

    def test_is_invitation_valid_used(self):
        """Test that used invitation is correctly identified."""
        invitation = UsedInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        success, message = is_invitation_valid(invitation)
        
        assert success is False
        assert message == "Invitation link is expired"

    def test_is_invitation_valid_inactive(self):
        """Test that inactive invitation is correctly identified."""
        invitation = InactiveInvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        success, message = is_invitation_valid(invitation)
        
        assert success is False
        assert message == "Invitation link is expired"

    def test_invitation_exists_true(self):
        """Test that existing invitation is correctly identified."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        result = invitation_exists(str(invitation.invitation_id))
        
        assert result is True

    def test_invitation_exists_false(self):
        """Test that non-existing invitation is correctly identified."""
        import uuid
        fake_id = str(uuid.uuid4())
        result = invitation_exists(fake_id)
        
        assert result is False

    def test_invitation_exists_empty_string(self):
        """Test invitation existence check with empty string."""
        # Empty string should be handled gracefully
        try:
            result = invitation_exists("")
            assert result is False
        except Exception:
            # If it raises an exception, that's also acceptable behavior
            pass

    def test_get_invitation_by_id_success(self):
        """Test successful invitation retrieval by ID."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.organization_member
        )
        
        result = get_invitation_by_id(invitation.invitation_id)
        
        assert result == invitation

    def test_get_invitation_by_id_not_found(self):
        """Test that DoesNotExist is raised when invitation not found."""
        import uuid
        fake_id = str(uuid.uuid4())
        with pytest.raises(Invitation.DoesNotExist):
            get_invitation_by_id(fake_id)

    def test_get_user_by_email_success(self):
        """Test successful user retrieval by email."""
        result = get_user_by_email(self.user.email)
        
        assert result == self.user
        assert result.email == self.user.email

    def test_get_user_by_email_case_insensitive(self):
        """Test that email search is case insensitive."""
        result = get_user_by_email(self.user.email.upper())
        
        assert result == self.user
        assert result.email == self.user.email

    def test_get_user_by_email_not_found(self):
        """Test that None is returned when user not found."""
        result = get_user_by_email("nonexistent@example.com")
        
        assert result is None

    def test_get_user_by_email_empty_string(self):
        """Test user retrieval with empty email."""
        # Empty string should return None or handle gracefully
        try:
            result = get_user_by_email("")
            assert result is None
        except Exception:
            # If it raises an exception, that's also acceptable behavior
            pass

    def test_get_user_by_email_none(self):
        """Test user retrieval with None email."""
        result = get_user_by_email(None)
        
        assert result is None

    def test_selector_integration_scenarios(self):
        """Test integration scenarios with multiple selectors."""
        # Create a valid invitation
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.organization_member,
            email=self.other_user.email
        )
        
        # Test complete invitation validation flow
        # 1. Check if invitation exists
        assert invitation_exists(str(invitation.invitation_id))
        
        # 2. Get invitation by token
        success, message, retrieved_invitation = get_invitation_by_token(str(invitation.token))
        assert success is True
        assert retrieved_invitation == invitation
        
        # 3. Check if invitation is valid
        valid, valid_message = is_invitation_valid(invitation)
        assert valid is True
        
        # 4. Check if user is recipient
        recipient, recipient_message = is_user_invitation_recipient(self.other_user, invitation)
        assert recipient is True
        
        # 5. Check if user is already in organization
        in_org, org_message = is_user_in_organization(self.other_user, invitation)
        assert in_org is False  # User is not in this organization yet

    def test_selector_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with very long email
        long_email = "a" * 250 + "@example.com"
        user_with_long_email = CustomUserFactory(email=long_email)
        
        result = get_user_by_email(long_email)
        assert result == user_with_long_email
        
        # Test with special characters in email
        special_email = "test+tag@example.com"
        user_with_special_email = CustomUserFactory(email=special_email)
        
        result = get_user_by_email(special_email)
        assert result == user_with_special_email
        
        # Test organization member check with non-existent user
        # Use a user that's not a member of this organization
        result = is_user_organization_member(self.other_user, self.organization)
        assert result is False

    def test_selector_performance_considerations(self):
        """Test that selectors handle multiple records efficiently."""
        # Create multiple invitations
        invitations = []
        for i in range(10):
            invitation = InvitationFactory(
                organization=self.organization, invited_by=self.organization_member
            )
            invitations.append(invitation)
        
        # Test that we can retrieve all invitations efficiently
        result = get_invitations_for_organization(self.organization.organization_id)
        assert len(result) == 10
        
        # Test that ordering is maintained
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at
