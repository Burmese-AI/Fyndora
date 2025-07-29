"""
Integration tests for invitation views.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from guardian.shortcuts import assign_perm

from apps.core.roles import get_permissions_for_role
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


@pytest.mark.integration
class TestInvitationViews(TestCase):
    """Integration test cases for invitation views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )

        # Make the user the organization owner to have necessary permissions
        self.organization.owner = self.member
        self.organization.save()

        # Assign organization owner permissions

        org_owner_group, _ = Group.objects.get_or_create(
            name=f"Org Owner - {self.organization.organization_id}"
        )

        # Get and assign all organization owner permissions
        org_owner_permissions = get_permissions_for_role("ORG_OWNER")
        for perm in org_owner_permissions:
            if "workspace_currency" not in perm:
                assign_perm(perm, org_owner_group, self.organization)

        # Add user to the organization owner group
        org_owner_group.user_set.add(self.user)

    def test_invitation_list_view_authenticated(self):
        """Test invitation list view for authenticated user."""
        # Create some invitations
        invitation1 = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )
        invitation2 = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        # Create invitation for different organization (should not appear)
        other_org = OrganizationFactory()
        other_member = OrganizationMemberFactory(organization=other_org)
        InvitationFactory(organization=other_org, invited_by=other_member)

        self.client.force_login(self.user)

        url = reverse(
            "invitation_list",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, invitation1.email)
        self.assertContains(response, invitation2.email)
        self.assertEqual(len(response.context["invitations"]), 2)

    def test_invitation_list_view_unauthenticated(self):
        """Test invitation list view for unauthenticated user."""
        url = reverse(
            "invitation_list",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_invitation_list_view_non_member(self):
        """Test invitation list view for non-organization member."""
        non_member = CustomUserFactory()
        self.client.force_login(non_member)

        url = reverse(
            "invitation_list",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.get(url)

        # Should return 403 or redirect
        self.assertIn(response.status_code, [403, 302])

    def test_invitation_create_view_get(self):
        """Test invitation create view GET request."""
        self.client.force_login(self.user)

        url = reverse(
            "invitation_create",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")
        self.assertContains(response, "email")
        self.assertContains(response, "expired_at")

    def test_invitation_create_view_post_valid(self):
        """Test invitation create view POST request with valid data."""
        self.client.force_login(self.user)

        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            "email": "test@example.com",
            "expired_at": future_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

        url = reverse(
            "invitation_create",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.post(url, data=form_data)

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Verify invitation was created
        invitation = Invitation.objects.get(email="test@example.com")
        self.assertEqual(invitation.organization, self.organization)
        self.assertEqual(invitation.invited_by, self.member)

    def test_invitation_create_view_post_invalid(self):
        """Test invitation create view POST request with invalid data."""
        self.client.force_login(self.user)

        # Invalid email and past date
        past_date = timezone.now() - timedelta(days=1)
        form_data = {
            "email": "invalid-email",
            "expired_at": past_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

        url = reverse(
            "invitation_create",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.post(url, data=form_data)

        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

        # Verify no invitation was created
        self.assertFalse(Invitation.objects.filter(email="invalid-email").exists())

    def test_invitation_create_view_existing_member(self):
        """Test invitation create view for existing organization member."""
        existing_user = CustomUserFactory(email="existing@example.com")
        OrganizationMemberFactory(organization=self.organization, user=existing_user)

        self.client.force_login(self.user)

        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            "email": "existing@example.com",
            "expired_at": future_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

        url = reverse(
            "invitation_create",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.post(url, data=form_data)

        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already a member")

        # Verify no invitation was created
        self.assertFalse(
            Invitation.objects.filter(
                email="existing@example.com", organization=self.organization
            ).exists()
        )

    def test_accept_invitation_view_valid(self):
        """Test accept invitation view with valid invitation."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")
        self.client.force_login(accepting_user)

        url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        response = self.client.get(url)

        # Should redirect after successful acceptance
        self.assertEqual(response.status_code, 302)

        # Verify invitation is marked as used
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)

        # Verify user is added to organization
        self.assertTrue(self.organization.members.filter(user=accepting_user).exists())

    def test_accept_invitation_view_invalid_token(self):
        """Test accept invitation view with invalid token."""
        accepting_user = CustomUserFactory()
        self.client.force_login(accepting_user)

        # Use a valid UUID format but non-existent token
        invalid_token = "12345678-1234-1234-1234-123456789abc"
        url = reverse("accept_invitation", kwargs={"invitation_token": invalid_token})
        response = self.client.get(url)

        # Should return error page or redirect with error
        self.assertIn(response.status_code, [400, 404, 302])

    def test_accept_invitation_view_expired(self):
        """Test accept invitation view with expired invitation."""
        invitation = ExpiredInvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")
        self.client.force_login(accepting_user)

        url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        response = self.client.get(url)

        # Should return error or redirect with error
        self.assertIn(response.status_code, [400, 302])

        # Verify invitation is not marked as used
        invitation.refresh_from_db()
        self.assertFalse(invitation.is_used)

    def test_accept_invitation_view_wrong_email(self):
        """Test accept invitation view with wrong email."""
        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        wrong_user = CustomUserFactory(email="wrong@example.com")
        self.client.force_login(wrong_user)

        url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        response = self.client.get(url)

        # Should return error or redirect with error
        self.assertIn(response.status_code, [400, 403, 302])

        # Verify invitation is not marked as used
        invitation.refresh_from_db()
        self.assertFalse(invitation.is_used)

    def test_accept_invitation_view_already_member(self):
        """Test accept invitation view when user is already a member."""
        accepting_user = CustomUserFactory(email="test@example.com")
        # Make user already a member
        OrganizationMemberFactory(organization=self.organization, user=accepting_user)

        invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        self.client.force_login(accepting_user)

        url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        response = self.client.get(url)

        # Should handle gracefully (redirect or show message)
        self.assertIn(response.status_code, [200, 302])

    def test_accept_invitation_view_unauthenticated(self):
        """Test accept invitation view for unauthenticated user."""
        invitation = InvitationFactory(
            organization=self.organization, invited_by=self.member
        )

        url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_accept_invitation_view_used_invitation(self):
        """Test accept invitation view with already used invitation."""
        invitation = UsedInvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )
        accepting_user = CustomUserFactory(email="test@example.com")
        self.client.force_login(accepting_user)

        url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        response = self.client.get(url)

        # Should return error or redirect with error
        self.assertIn(response.status_code, [400, 302])

    def test_invitation_workflow_end_to_end(self):
        """Test complete invitation workflow from creation to acceptance."""
        # Step 1: Create invitation
        self.client.force_login(self.user)

        future_date = timezone.now() + timedelta(days=7)
        form_data = {
            "email": "newuser@example.com",
            "expired_at": future_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

        create_url = reverse(
            "invitation_create",
            kwargs={"organization_id": self.organization.organization_id},
        )
        response = self.client.post(create_url, data=form_data)

        self.assertEqual(response.status_code, 302)

        # Verify invitation was created
        invitation = Invitation.objects.get(email="newuser@example.com")
        self.assertEqual(invitation.organization, self.organization)

        # Step 2: Accept invitation
        new_user = CustomUserFactory(email="newuser@example.com")
        self.client.force_login(new_user)

        accept_url = reverse(
            "accept_invitation", kwargs={"invitation_token": invitation.token}
        )
        response = self.client.get(accept_url)

        self.assertEqual(response.status_code, 302)

        # Verify invitation is used and user is member
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)
        self.assertTrue(self.organization.members.filter(user=new_user).exists())
