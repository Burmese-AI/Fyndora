"""
Integration tests for the complete invitation workflow.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone

from apps.invitations import selectors, services
from apps.invitations.models import Invitation
from apps.organizations.models import OrganizationMember
from tests.factories import (
    ExpiredInvitationFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)

User = get_user_model()


@pytest.mark.integration
class TestInvitationWorkflow(TransactionTestCase):
    """Integration test cases for the complete invitation workflow."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationFactory()
        self.admin_user = CustomUserFactory()
        self.admin_member = OrganizationMemberFactory(
            organization=self.organization, user=self.admin_user
        )

    def test_complete_invitation_workflow_success(self):
        """Test complete invitation workflow from creation to acceptance."""
        # Step 1: Create invitation
        email = "newuser@example.com"
        expired_at = timezone.now() + timedelta(days=7)

        invitation = services.create_invitation(
            organization=self.organization,
            invited_by=self.admin_member,
            email=email,
            expired_at=expired_at,
        )

        # Verify invitation creation
        self.assertIsInstance(invitation, Invitation)
        self.assertEqual(invitation.email, email)
        self.assertTrue(invitation.is_valid)

        # Step 2: Create user and verify invitation
        new_user = CustomUserFactory(email=email)
        is_verified, message, verified_invitation = services.verify_invitation_for_acceptance(
            user=new_user, invitation_token=invitation.token
        )

        self.assertTrue(is_verified)
        self.assertEqual(verified_invitation, invitation)

        # Step 3: Accept invitation

        # Verify user is not a member yet
        self.assertFalse(
            selectors.is_user_organization_member(
                user=new_user, organization=self.organization
            )
        )

        # Accept invitation
        result = services.accept_invitation(invitation=invitation, user=new_user)

        self.assertTrue(result)

        # Step 4: Verify final state
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)
        self.assertFalse(invitation.is_valid)

        # Verify user is now a member
        self.assertTrue(
            selectors.is_user_organization_member(
                user=new_user, organization=self.organization
            )
        )

        # Verify organization member was created
        member = OrganizationMember.objects.get(
            organization=self.organization, user=new_user
        )
        self.assertIsNotNone(member)

    def test_invitation_workflow_with_deactivation(self):
        """Test invitation workflow with deactivation of previous invitations."""
        email = "user@example.com"

        # Step 1: Create first invitation
        expired_at = timezone.now() + timedelta(days=7)
        invitation1 = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.admin_member,
        )

        # Step 2: Create second invitation for same email
        invitation2 = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.admin_member,
        )

        # Step 3: Deactivate unused invitations
        count = services.deactivate_all_unused_active_invitations(
            organization=self.organization, email=email
        )

        self.assertEqual(count, 2)

        # Verify both invitations are deactivated
        invitation1.refresh_from_db()
        invitation2.refresh_from_db()
        self.assertFalse(invitation1.is_active)
        self.assertFalse(invitation2.is_active)
        self.assertFalse(invitation1.is_valid)
        self.assertFalse(invitation2.is_valid)

    def test_invitation_workflow_expired_invitation(self):
        """Test invitation workflow with expired invitation."""
        email = "user@example.com"

        # Create expired invitation
        invitation = ExpiredInvitationFactory(
            organization=self.organization, invited_by=self.admin_member, email=email
        )

        # Verify invitation is expired
        self.assertTrue(invitation.is_expired)
        self.assertFalse(invitation.is_valid)

        # Create user and try to verify expired invitation
        user = CustomUserFactory(email=email)
        is_verified, message, verified_invitation = services.verify_invitation_for_acceptance(
            user=user, invitation_token=invitation.token
        )

        self.assertFalse(is_verified)
        self.assertIsNone(verified_invitation)

        # Try to accept expired invitation
        result = services.accept_invitation(invitation=invitation, user=user)

        self.assertFalse(result)

        # Verify user is not a member
        self.assertFalse(
            selectors.is_user_organization_member(
                user=user, organization=self.organization
            )
        )

    def test_invitation_workflow_wrong_email(self):
        """Test invitation workflow with wrong email."""
        invitation_email = "invited@example.com"
        wrong_email = "wrong@example.com"

        # Create invitation
        expired_at = timezone.now() + timedelta(days=7)
        invitation = services.create_invitation(
            email=invitation_email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.admin_member,
        )

        # Try to verify with wrong email
        wrong_user = CustomUserFactory(email=wrong_email)
        is_verified, message, verified_invitation = services.verify_invitation_for_acceptance(
            user=wrong_user, invitation_token=invitation.token
        )

        self.assertFalse(is_verified)
        self.assertIsNone(verified_invitation)

        # Try to accept with wrong email
        result = services.accept_invitation(invitation=invitation, user=wrong_user)

        self.assertFalse(result)

        # Verify invitation is not used
        invitation.refresh_from_db()
        self.assertFalse(invitation.is_used)

    def test_invitation_workflow_already_member(self):
        """Test invitation workflow when user is already a member."""
        email = "member@example.com"

        # Create user and make them a member
        existing_user = CustomUserFactory(email=email)
        OrganizationMemberFactory(organization=self.organization, user=existing_user)

        # Create invitation
        expired_at = timezone.now() + timedelta(days=7)
        invitation = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.admin_member,
        )

        # Verify invitation is created but validation fails
        is_verified, message, verified_invitation = services.verify_invitation_for_acceptance(
            user=existing_user, invitation_token=invitation.token
        )

        self.assertFalse(is_verified)
        self.assertIsNone(verified_invitation)

        # Try to accept invitation
        result = services.accept_invitation(invitation=invitation, user=existing_user)

        self.assertFalse(result)

    def test_invitation_workflow_multiple_organizations(self):
        """Test invitation workflow across multiple organizations."""
        email = "user@example.com"

        # Create second organization
        org2 = OrganizationFactory()
        admin2 = CustomUserFactory()
        member2 = OrganizationMemberFactory(organization=org2, user=admin2)

        # Create invitations for both organizations
        expired_at = timezone.now() + timedelta(days=7)
        invitation1 = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.admin_member,
        )

        invitation2 = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=org2,
            invited_by=member2,
        )

        # Create user
        user = CustomUserFactory(email=email)

        # Accept first invitation
        result1 = services.accept_invitation(invitation=invitation1, user=user)

        self.assertTrue(result1)

        # Verify user is member of first organization
        self.assertTrue(
            selectors.is_user_organization_member(
                user=user, organization=self.organization
            )
        )

        # Accept second invitation
        result2 = services.accept_invitation(invitation=invitation2, user=user)

        self.assertTrue(result2)

        # Verify user is member of both organizations
        self.assertTrue(
            selectors.is_user_organization_member(user=user, organization=org2)
        )

        # Verify both invitations are used
        invitation1.refresh_from_db()
        invitation2.refresh_from_db()
        self.assertTrue(invitation1.is_used)
        self.assertTrue(invitation2.is_used)

    def test_invitation_workflow_database_integrity(self):
        """Test invitation workflow maintains database integrity."""
        email = "user@example.com"

        # Create invitation
        expired_at = timezone.now() + timedelta(days=7)
        invitation = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.admin_member,
        )

        # Verify database state
        self.assertEqual(Invitation.objects.count(), 1)
        self.assertEqual(OrganizationMember.objects.count(), 1)  # Only admin

        # Create user and accept invitation
        user = CustomUserFactory(email=email)

        with transaction.atomic():
            result = services.accept_invitation(invitation=invitation, user=user)

        self.assertTrue(result)

        # Verify final database state
        self.assertEqual(Invitation.objects.count(), 1)
        self.assertEqual(OrganizationMember.objects.count(), 2)  # Admin + new user

        # Verify invitation is properly updated
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)

        # Verify organization member is properly created
        new_member = OrganizationMember.objects.get(user=user)
        self.assertEqual(new_member.organization, self.organization)

    def test_invitation_workflow_concurrent_acceptance(self):
        """Test invitation workflow with concurrent acceptance attempts."""
        email = "user@example.com"

        # Create invitation
        expired_at = timezone.now() + timedelta(days=7)
        invitation = services.create_invitation(
            email=email,
            expired_at=expired_at,
            organization=self.organization,
            invited_by=self.admin_member,
        )

        # Create user
        user = CustomUserFactory(email=email)

        # Simulate concurrent acceptance
        # First acceptance should succeed
        result1 = services.accept_invitation(invitation=invitation, user=user)

        self.assertTrue(result1)

        # Second acceptance should fail (invitation already used)
        result2 = services.accept_invitation(invitation=invitation, user=user)

        self.assertFalse(result2)

        # Verify only one organization member exists
        member_count = OrganizationMember.objects.filter(
            organization=self.organization, user=user
        ).count()

        self.assertEqual(member_count, 1)
