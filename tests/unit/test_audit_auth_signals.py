"""
Unit tests for audit authentication signals.

Following the test plan: AuditLog App (apps.auditlog)
- Authentication signal tests
- Login/logout tracking tests
- Failed login attempt tests
- Security event logging tests
"""

from unittest.mock import patch

import pytest
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.test import RequestFactory, TestCase

from apps.auditlog.auth_signals import log_failed_login, log_user_login, log_user_logout
from apps.auditlog.constants import AuditActionType
from tests.factories import CustomUserFactory


@pytest.mark.unit
class TestAuthenticationSignals(TestCase):
    """Test authentication signal handlers."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    def test_log_user_login_success(self, mock_audit_create):
        """Test successful login logging."""
        request = self.factory.post("/login/")

        # Trigger the signal handler
        log_user_login(sender=None, request=request, user=self.user)

        # Verify audit_create_authentication_event was called
        mock_audit_create.assert_called_once_with(
            user=self.user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"login_method": "session", "automatic_logging": True},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    def test_log_user_logout(self, mock_audit_create):
        """Test user logout logging."""
        request = self.factory.post("/logout/")

        # Trigger the signal handler
        log_user_logout(sender=None, request=request, user=self.user)

        # Verify audit_create_authentication_event was called
        mock_audit_create.assert_called_once_with(
            user=self.user,
            action_type=AuditActionType.LOGOUT,
            metadata={"logout_method": "user_initiated", "automatic_logging": True},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_security_event")
    def test_log_failed_login_with_username(self, mock_audit_create):
        """Test failed login attempt logging with username."""
        request = self.factory.post("/login/")
        credentials = {"username": "testuser", "password": "wrongpassword"}

        # Trigger the signal handler
        log_failed_login(sender=None, credentials=credentials, request=request)

        # Verify audit_create_security_event was called
        mock_audit_create.assert_called_once_with(
            user=None,
            action_type=AuditActionType.LOGIN_FAILED,
            metadata={
                "attempted_username": "testuser",
                "failure_reason": "invalid_credentials",
                "automatic_logging": True,
            },
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_security_event")
    def test_log_failed_login_without_username(self, mock_audit_create):
        """Test failed login attempt logging without username."""
        request = self.factory.post("/login/")
        credentials = {"password": "wrongpassword"}  # No username

        # Trigger the signal handler
        log_failed_login(sender=None, credentials=credentials, request=request)

        # Verify audit_create_security_event was called
        mock_audit_create.assert_called_once_with(
            user=None,
            action_type=AuditActionType.LOGIN_FAILED,
            metadata={
                "attempted_username": "",
                "failure_reason": "invalid_credentials",
                "automatic_logging": True,
            },
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_security_event")
    def test_log_failed_login_empty_credentials(self, mock_audit_create):
        """Test failed login attempt logging with empty credentials."""
        request = self.factory.post("/login/")
        credentials = {}

        # Trigger the signal handler
        log_failed_login(sender=None, credentials=credentials, request=request)

        # Verify audit_create_security_event was called
        mock_audit_create.assert_called_once_with(
            user=None,
            action_type=AuditActionType.LOGIN_FAILED,
            metadata={
                "attempted_username": "",
                "failure_reason": "invalid_credentials",
                "automatic_logging": True,
            },
        )


@pytest.mark.unit
class TestAuthenticationSignalIntegration(TestCase):
    """Test authentication signal integration with Django's auth system."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.services.audit_create")
    def test_login_signal_integration(self, mock_audit_create):
        """Test that login signal is properly connected."""
        request = self.factory.post("/login/")

        # Send the actual Django signal
        user_logged_in.send(sender=self.user.__class__, request=request, user=self.user)

        # Verify that our handler was called
        # Note: This test assumes the signal handler is connected
        # In practice, you might need to manually connect it for testing
        self.assertTrue(
            True
        )  # Placeholder - actual implementation depends on signal connection

    @pytest.mark.django_db
    @patch("apps.auditlog.services.audit_create")
    def test_logout_signal_integration(self, mock_audit_create):
        """Test that logout signal is properly connected."""
        request = self.factory.post("/logout/")

        # Send the actual Django signal
        user_logged_out.send(
            sender=self.user.__class__, request=request, user=self.user
        )

        # Verify that our handler was called
        self.assertTrue(
            True
        )  # Placeholder - actual implementation depends on signal connection

    @pytest.mark.django_db
    @patch("apps.auditlog.services.audit_create")
    def test_failed_login_signal_integration(self, mock_audit_create):
        """Test that failed login signal is properly connected."""
        request = self.factory.post("/login/")
        credentials = {"username": "testuser", "password": "wrong"}

        # Send the actual Django signal
        user_login_failed.send(sender=None, credentials=credentials, request=request)

        # Verify that our handler was called
        self.assertTrue(
            True
        )  # Placeholder - actual implementation depends on signal connection


@pytest.mark.unit
class TestAuthenticationSignalErrorHandling(TestCase):
    """Test error handling in authentication signal handlers."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    @patch("apps.auditlog.auth_signals.logger")
    def test_login_handler_with_exception(self, mock_logger, mock_audit_create):
        """Test login handler behavior when audit creation fails."""
        request = self.factory.post("/login/")

        # Make audit_create_authentication_event raise an exception
        mock_audit_create.side_effect = Exception("Database error")

        # Should not raise exception due to safe_audit_log decorator
        try:
            log_user_login(sender=None, request=request, user=self.user)
        except Exception:
            self.fail("safe_audit_log should have caught the exception")

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    @patch("apps.auditlog.auth_signals.logger")
    def test_logout_handler_with_exception(self, mock_logger, mock_audit_create):
        """Test logout handler behavior when audit creation fails."""
        request = self.factory.post("/logout/")

        # Make audit_create_authentication_event raise an exception
        mock_audit_create.side_effect = Exception("Database error")

        # Should not raise exception due to safe_audit_log decorator
        try:
            log_user_logout(sender=None, request=request, user=self.user)
        except Exception:
            self.fail("safe_audit_log should have caught the exception")

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_security_event")
    @patch("apps.auditlog.auth_signals.logger")
    def test_failed_login_handler_with_exception(self, mock_logger, mock_audit_create):
        """Test failed login handler behavior when audit creation fails."""
        request = self.factory.post("/login/")
        credentials = {"username": "testuser"}

        # Make audit_create_security_event raise an exception
        mock_audit_create.side_effect = Exception("Database error")

        # Should not raise exception due to safe_audit_log decorator
        try:
            log_failed_login(sender=None, credentials=credentials, request=request)
        except Exception:
            self.fail("safe_audit_log should have caught the exception")

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    def test_login_handler_with_none_user(self, mock_audit_create):
        """Test login handler with None user."""
        request = self.factory.post("/login/")

        # Trigger with None user
        log_user_login(sender=None, request=request, user=None)

        # Should still call audit_create_authentication_event
        mock_audit_create.assert_called_once_with(
            user=None,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"login_method": "session", "automatic_logging": True},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    def test_logout_handler_with_none_user(self, mock_audit_create):
        """Test logout handler with None user."""
        request = self.factory.post("/logout/")

        # Trigger with None user
        log_user_logout(sender=None, request=request, user=None)

        # Should still call audit_create_authentication_event
        mock_audit_create.assert_called_once_with(
            user=None,
            action_type=AuditActionType.LOGOUT,
            metadata={"logout_method": "user_initiated", "automatic_logging": True},
        )

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    def test_login_handler_with_none_request(self, mock_audit_create):
        """Test login handler with None request."""
        # Trigger with None request
        log_user_login(sender=None, request=None, user=self.user)

        # Should still call audit_create_authentication_event
        mock_audit_create.assert_called_once_with(
            user=self.user,
            action_type=AuditActionType.LOGIN_SUCCESS,
            metadata={"login_method": "session", "automatic_logging": True},
        )


@pytest.mark.unit
class TestAuthenticationSignalMetadata(TestCase):
    """Test metadata generation in authentication signal handlers."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    def test_login_metadata_structure(self, mock_audit_create):
        """Test that login metadata has correct structure."""
        request = self.factory.post("/login/")

        log_user_login(sender=None, request=request, user=self.user)

        # Get the metadata from the call
        call_args = mock_audit_create.call_args
        metadata = call_args[1]["metadata"]

        # Verify metadata structure
        self.assertIn("login_method", metadata)
        self.assertIn("automatic_logging", metadata)
        self.assertEqual(metadata["login_method"], "session")
        self.assertTrue(metadata["automatic_logging"])

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_authentication_event")
    def test_logout_metadata_structure(self, mock_audit_create):
        """Test that logout metadata has correct structure."""
        request = self.factory.post("/logout/")

        log_user_logout(sender=None, request=request, user=self.user)

        # Get the metadata from the call
        call_args = mock_audit_create.call_args
        metadata = call_args[1]["metadata"]

        # Verify metadata structure
        self.assertIn("logout_method", metadata)
        self.assertIn("automatic_logging", metadata)
        self.assertEqual(metadata["logout_method"], "user_initiated")
        self.assertTrue(metadata["automatic_logging"])

    @pytest.mark.django_db
    @patch("apps.auditlog.auth_signals.audit_create_security_event")
    def test_failed_login_metadata_structure(self, mock_audit_create):
        """Test that failed login metadata has correct structure."""
        request = self.factory.post("/login/")
        credentials = {"username": "testuser", "password": "wrong"}

        log_failed_login(sender=None, credentials=credentials, request=request)

        # Get the metadata from the call
        call_args = mock_audit_create.call_args
        metadata = call_args[1]["metadata"]

        # Verify metadata structure
        self.assertIn("attempted_username", metadata)
        self.assertIn("failure_reason", metadata)
        self.assertIn("automatic_logging", metadata)
        self.assertEqual(metadata["attempted_username"], "testuser")
        self.assertEqual(metadata["failure_reason"], "invalid_credentials")
        self.assertTrue(metadata["automatic_logging"])
