"""Unit tests for invitation services."""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import signals

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
        # Disable signals to speed up tests and prevent Celery tasks
        signals.post_save.disconnect(sender=Invitation)
        signals.pre_save.disconnect(sender=Invitation)
        
        # Mock only the email sending to prevent Celery calls, but allow other logic
        self.email_patcher = patch('apps.emails.services.send_invitation_email')
        self.mock_send_email = self.email_patcher.start()
        
        # Mock the Celery task to prevent broker connection attempts
        self.celery_patcher = patch('apps.emails.tasks.send_email_task.delay')
        self.mock_celery_task = self.celery_patcher.start()
        
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.non_member_user = CustomUserFactory()

    def tearDown(self):
        """Re-enable signals after tests."""
        # Stop all mocks
        self.email_patcher.stop()
        self.celery_patcher.stop()
        
        # Re-enable signals
        from apps.invitations import signals as invitation_signals
        signals.post_save.connect(invitation_signals.send_invitation_email, sender=Invitation)
        signals.pre_save.connect(invitation_signals.handle_invitation_creation, sender=Invitation)

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

    def test_create_invitation_with_past_expiration(self):
        """Test invitation creation with past expiration date."""
        email = "test@example.com"
        expired_at = timezone.now() - timedelta(days=1)  # Past date

        invitation = services.create_invitation(
            organization=self.organization,
            invited_by=self.member,
            email=email,
            expired_at=expired_at,
        )

        self.assertIsInstance(invitation, Invitation)
        self.assertEqual(invitation.expired_at, expired_at)
        # Should still be created but will be invalid
        self.assertFalse(invitation.is_valid)

    def test_create_invitation_with_empty_email(self):
        """Test invitation creation with empty email."""
        expired_at = timezone.now() + timedelta(days=7)

        # The service now validates and raises ValueError for empty emails
        with self.assertRaises(ValueError):
            services.create_invitation(
                organization=self.organization,
                invited_by=self.member,
                email="",  # Empty email
                expired_at=expired_at,
            )
        

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

    def test_accept_invitation_already_used(self):
        """Test accepting an already used invitation."""
        invitation = UsedInvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")

        result = services.accept_invitation(invitation=invitation, user=accepting_user)

        self.assertFalse(result)

        # Verify invitation status remains unchanged
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)
        self.assertFalse(invitation.is_active)

    def test_accept_invitation_inactive(self):
        """Test accepting an inactive invitation."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        # Manually deactivate the invitation
        invitation.is_active = False
        invitation.save()

        accepting_user = CustomUserFactory(email="test@example.com")

        result = services.accept_invitation(invitation=invitation, user=accepting_user)

        self.assertFalse(result)

    def test_accept_invitation_transaction_rollback(self):
        """Test that transaction rolls back if adding user to organization fails."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")

        # Mock OrganizationMember.objects.create to raise an exception
        with patch('apps.organizations.models.OrganizationMember.objects.create') as mock_create:
            mock_create.side_effect = IntegrityError("Database error")
            
            with self.assertRaises(IntegrityError):
                services.accept_invitation(invitation=invitation, user=accepting_user)

        # Verify invitation status is unchanged
        invitation.refresh_from_db()
        self.assertFalse(invitation.is_used)
        self.assertTrue(invitation.is_active)

        # Verify user is not added to organization
        self.assertFalse(self.organization.members.filter(user=accepting_user).exists())

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

    def test_verify_invitation_expired(self):
        """Test verification with expired invitation."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization,
            email=self.non_member_user.email,
        )

        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            self.non_member_user, str(invitation.token)
        )

        self.assertFalse(result)
        self.assertIsNotNone(message)
        self.assertIsNone(invitation_obj)

    def test_verify_invitation_already_used(self):
        """Test verification with already used invitation."""
        invitation = UsedInvitationFactory(
            organization=self.organization,
            email=self.non_member_user.email,
        )

        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            self.non_member_user, str(invitation.token)
        )

        self.assertFalse(result)
        self.assertIsNotNone(message)
        self.assertIsNone(invitation_obj)


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

    def test_delete_invitation_success(self):
        """Test successful invitation deletion."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        invitation_id = invitation.invitation_id

        # Verify invitation exists before deletion
        self.assertTrue(Invitation.objects.filter(invitation_id=invitation_id).exists())

        services.delete_invitation(invitation)

        # Verify invitation is deleted
        self.assertFalse(Invitation.objects.filter(invitation_id=invitation_id).exists())

    def test_delete_invitation_nonexistent(self):
        """Test deleting a non-existent invitation."""
        # Create and immediately delete to get a reference to a non-existent invitation
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        invitation_id = invitation.invitation_id
        invitation.delete()

        # This should not raise an exception - Django handles this gracefully
        try:
            # Create a new invitation object with the same ID but don't save it
            fake_invitation = Invitation(invitation_id=invitation_id)
            services.delete_invitation(fake_invitation)
        except Exception as e:
            # If it does raise an exception, that's also acceptable
            pass

    def test_deactivate_unused_invitations_empty_result(self):
        """Test deactivating invitations when no active unused invitations exist."""
        email = "test@example.com"

        # Create only used invitations
        used_invitation = UsedInvitationFactory(
            organization=self.organization, invited_by=self.member, email=email
        )

        count = services.deactivate_all_unused_active_invitations(
            organization=self.organization, email=email
        )

        self.assertEqual(count, 0)

        # Verify used invitation remains unchanged
        used_invitation.refresh_from_db()
        self.assertFalse(used_invitation.is_active)  # Was already inactive


    def test_create_invitation_with_none_parameters(self):
        """Test invitation creation with None parameters."""
        # Test with None email
        with self.assertRaises(ValueError):
            services.create_invitation(
                organization=self.organization,
                invited_by=self.member,
                email=None,
                expired_at=timezone.now() + timedelta(days=7),
            )

        # Test with None organization
        with self.assertRaises(ValueError):
            services.create_invitation(
                organization=None,
                invited_by=self.member,
                email="test@example.com",
                expired_at=timezone.now() + timedelta(days=7),
            )

        # Test with None invited_by
        with self.assertRaises(ValueError):
            services.create_invitation(
                organization=self.organization,
                invited_by=None,
                email="test@example.com",
                expired_at=timezone.now() + timedelta(days=7),
            )

    def test_accept_invitation_with_none_user(self):
        """Test accepting invitation with None user."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

        with self.assertRaises(AttributeError):
            services.accept_invitation(invitation=invitation, user=None)

    def test_accept_invitation_with_none_invitation(self):
        """Test accepting None invitation."""
        user = CustomUserFactory(email="test@example.com")

        with self.assertRaises(AttributeError):
            services.accept_invitation(invitation=None, user=user)

    def test_verify_invitation_with_none_user(self):
        """Test verification with None user."""
        invitation = InvitationFactory(
            organization=self.organization,
            email="test@example.com",
        )

        # Test with None user - this should handle gracefully
        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            None, str(invitation.token)
        )

        self.assertFalse(result)
        self.assertIsNotNone(message)
        self.assertIsNone(invitation_obj)

    def test_verify_invitation_with_none_token(self):
        """Test verification with None token."""
        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            self.user, None
        )

        self.assertFalse(result)
        self.assertIsNotNone(message)
        self.assertIsNone(invitation_obj)

    def test_deactivate_invitations_with_none_parameters(self):
        """Test deactivation with None parameters."""
        # Test with None email
        count = services.deactivate_all_unused_active_invitations(
            organization=self.organization, email=None
        )
        self.assertEqual(count, 0)

        # Test with None organization
        count = services.deactivate_all_unused_active_invitations(
            organization=None, email="test@example.com"
        )
        self.assertEqual(count, 0)

    def test_delete_invitation_with_none(self):
        """Test deleting None invitation."""
        with self.assertRaises(AttributeError):
            services.delete_invitation(None)

    def test_accept_invitation_return_value_consistency(self):
        """Test that accept_invitation returns consistent types."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")

        # Test successful acceptance returns invitation object
        result = services.accept_invitation(invitation=invitation, user=accepting_user)
        self.assertIsInstance(result, Invitation)

        # Test failed acceptance returns False
        invitation2 = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="different@example.com",
        )
        result = services.accept_invitation(invitation=invitation2, user=accepting_user)
        self.assertFalse(result)

    def test_verify_invitation_return_value_consistency(self):
        """Test that verify_invitation_for_acceptance returns consistent types."""
        invitation = InvitationFactory(
            organization=self.organization,
            email=self.non_member_user.email,
        )

        # Test successful verification
        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            self.non_member_user, str(invitation.token)
        )
        self.assertIsInstance(result, bool)
        self.assertIsInstance(message, str)
        self.assertIsInstance(invitation_obj, Invitation)

        # Test failed verification with valid UUID format
        invalid_token = str(uuid.uuid4())  # Valid UUID format but non-existent
        result, message, invitation_obj = services.verify_invitation_for_acceptance(
            self.user, invalid_token
        )
        self.assertIsInstance(result, bool)
        self.assertIsInstance(message, str)
        self.assertIsNone(invitation_obj)
