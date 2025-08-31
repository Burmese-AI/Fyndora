"""Unit tests for invitation utils."""

import pytest
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.db.models import signals
from unittest.mock import patch

from apps.invitations import utils
from apps.invitations.models import Invitation
from tests.factories import (
    InvitationFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    CustomUserFactory,
)


@pytest.mark.unit
class TestInvitationUtils(TestCase):
    """Test cases for invitation utils."""

    def setUp(self):
        """Set up test data."""
        # Disable signals to speed up tests and prevent Celery tasks
        signals.post_save.disconnect(sender=Invitation)
        signals.pre_save.disconnect(sender=Invitation)

        # Mock only the email sending to prevent Celery calls, but allow other logic
        self.email_patcher = patch("apps.emails.services.send_invitation_email")
        self.mock_send_email = self.email_patcher.start()

        # Mock the Celery task to prevent broker connection attempts
        self.celery_patcher = patch("apps.emails.tasks.send_email_task.delay")
        self.mock_celery_task = self.celery_patcher.start()

        self.factory = RequestFactory()
        self.organization = OrganizationFactory()
        self.user = CustomUserFactory()
        self.member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )
        self.invitation = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test@example.com",
        )

    def tearDown(self):
        """Re-enable signals after tests."""
        # Stop all mocks
        self.email_patcher.stop()
        self.celery_patcher.stop()

        # Re-enable signals
        from apps.invitations import signals as invitation_signals

        signals.post_save.connect(
            invitation_signals.send_invitation_email, sender=Invitation
        )
        signals.pre_save.connect(
            invitation_signals.handle_invitation_creation, sender=Invitation
        )

    def test_get_invitation_url_with_request(self):
        """Test building invitation URL using request object."""
        request = self.factory.get("/")

        url = utils.get_invitation_url(request=request, invitation=self.invitation)

        expected_path = reverse(
            "accept_invitation", kwargs={"invitation_token": self.invitation.token}
        )
        expected_url = request.build_absolute_uri(expected_path)

        self.assertEqual(url, expected_url)
        self.assertTrue(url.startswith("http://testserver"))
        self.assertIn(str(self.invitation.token), url)

    def test_get_invitation_url_with_domain_override(self):
        """Test building invitation URL using domain override."""
        domain = "example.com"

        url = utils.get_invitation_url(
            invitation=self.invitation, domain_override=domain
        )

        expected_path = reverse(
            "accept_invitation", kwargs={"invitation_token": self.invitation.token}
        )
        expected_url = f"https://{domain}{expected_path}"

        self.assertEqual(url, expected_url)
        self.assertTrue(url.startswith("https://example.com"))
        self.assertIn(str(self.invitation.token), url)

    def test_get_invitation_url_with_none_invitation(self):
        """Test that ValueError is raised when invitation is None."""
        request = self.factory.get("/")

        with self.assertRaises(ValueError) as context:
            utils.get_invitation_url(request=request, invitation=None)

        self.assertEqual(str(context.exception), "invitation is required")

    def test_get_invitation_url_without_request_and_domain(self):
        """Test that ValueError is raised when neither request nor domain_override is provided."""
        with self.assertRaises(ValueError) as context:
            utils.get_invitation_url(invitation=self.invitation)

        self.assertEqual(
            str(context.exception), "Either request or domain_override is required"
        )

    def test_get_invitation_url_with_empty_domain_override(self):
        """Test that ValueError is raised when domain_override is empty string."""
        with self.assertRaises(ValueError) as context:
            utils.get_invitation_url(invitation=self.invitation, domain_override="")

        self.assertEqual(
            str(context.exception), "Either request or domain_override is required"
        )

    def test_get_invitation_url_with_whitespace_domain_override(self):
        """Test that ValueError is raised when domain_override is only whitespace."""
        with self.assertRaises(ValueError) as context:
            utils.get_invitation_url(invitation=self.invitation, domain_override="   ")

        self.assertEqual(
            str(context.exception), "Either request or domain_override is required"
        )

    def test_get_invitation_url_with_both_request_and_domain(self):
        """Test that request takes precedence when both are provided."""
        request = self.factory.get("/")
        domain = "example.com"

        url = utils.get_invitation_url(
            request=request, invitation=self.invitation, domain_override=domain
        )

        # Should use request, not domain_override
        expected_path = reverse(
            "accept_invitation", kwargs={"invitation_token": self.invitation.token}
        )
        expected_url = request.build_absolute_uri(expected_path)

        self.assertEqual(url, expected_url)
        self.assertTrue(url.startswith("http://testserver"))
        self.assertNotIn("https://example.com", url)

    def test_get_invitation_url_different_invitation_tokens(self):
        """Test that different invitations generate different URLs."""
        invitation2 = InvitationFactory(
            organization=self.organization,
            invited_by=self.member,
            email="test2@example.com",
        )

        request = self.factory.get("/")

        url1 = utils.get_invitation_url(request=request, invitation=self.invitation)
        url2 = utils.get_invitation_url(request=request, invitation=invitation2)

        self.assertNotEqual(url1, url2)
        self.assertIn(str(self.invitation.token), url1)
        self.assertIn(str(invitation2.token), url2)

    def test_get_invitation_url_with_https_request(self):
        """Test building URL with HTTPS request."""
        request = self.factory.get("/", secure=True)

        url = utils.get_invitation_url(request=request, invitation=self.invitation)

        self.assertTrue(url.startswith("https://"))

    def test_get_invitation_url_with_custom_domain_format(self):
        """Test building URL with custom domain formats."""
        test_cases = [
            "example.com",
            "www.example.com",
            "subdomain.example.com",
            "example.co.uk",
            "example-domain.com",
        ]

        for domain in test_cases:
            url = utils.get_invitation_url(
                invitation=self.invitation, domain_override=domain
            )

            expected_path = reverse(
                "accept_invitation", kwargs={"invitation_token": self.invitation.token}
            )
            expected_url = f"https://{domain}{expected_path}"

            self.assertEqual(url, expected_url)
            self.assertTrue(url.startswith(f"https://{domain}"))

    def test_get_invitation_url_invitation_properties(self):
        """Test that the generated URL contains correct invitation properties."""
        request = self.factory.get("/")

        url = utils.get_invitation_url(request=request, invitation=self.invitation)

        # URL should contain the invitation token
        self.assertIn(str(self.invitation.token), url)

        # URL should contain the accept_invitation path
        self.assertIn("/invitations/", url)

        # URL should be absolute (start with http/https)
        self.assertTrue(url.startswith(("http://", "https://")))

    def test_get_invitation_url_error_messages(self):
        """Test that appropriate error messages are returned."""
        # Test None invitation error
        with self.assertRaises(ValueError) as context:
            utils.get_invitation_url(invitation=None)
        self.assertEqual(str(context.exception), "invitation is required")

        # Test missing request and domain error
        with self.assertRaises(ValueError) as context:
            utils.get_invitation_url(invitation=self.invitation)
        self.assertEqual(
            str(context.exception), "Either request or domain_override is required"
        )

    def test_get_invitation_url_with_none_request(self):
        """Test that None request is handled properly."""
        domain = "example.com"

        url = utils.get_invitation_url(
            invitation=self.invitation, domain_override=domain
        )

        expected_path = reverse(
            "accept_invitation", kwargs={"invitation_token": self.invitation.token}
        )
        expected_url = f"https://{domain}{expected_path}"

        self.assertEqual(url, expected_url)
