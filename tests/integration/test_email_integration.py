"""
Integration tests for email services and background tasks.

This module contains comprehensive integration tests that verify the complete
email flow from service calls through task execution to actual email delivery.
"""

from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from apps.emails.adapters import CustomAccountAdapter
from apps.emails.services import (
    send_password_reset_email,
    send_signup_confirmation_email,
)
from apps.emails.tasks import send_email_task
from tests.factories import CustomUserFactory


@pytest.mark.integration
class TestEmailFlowIntegration(TestCase):
    """
    Test complete email flow integration from services to tasks.
    """

    def setUp(self):
        """Set up test data."""
        self.users = [CustomUserFactory() for _ in range(3)]
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    @patch("apps.emails.services.send_email_task.delay")
    def test_complete_signup_confirmation_flow(self, mock_task):
        """Test complete signup confirmation email flow."""
        # Setup
        mock_task.return_value = Mock(id="task_123")
        
        user = self.users[0]
        # Mock the user method directly on the instance
        user.get_confirmation_url = Mock(return_value="http://example.com/confirm/123")
        
        # Execute
        send_signup_confirmation_email(user)
        
        # Verify task was called with correct parameters
        mock_task.assert_called_once()
        call_args = mock_task.call_args[1]
        
        self.assertEqual(call_args['to'], user.email)
        self.assertEqual(call_args['subject'], "Confirm your email address")
        self.assertIn("http://example.com/confirm/123", call_args['contents'])
        
        # Verify user method was called
        user.get_confirmation_url.assert_called_once()

    @patch('apps.emails.services.send_email_task.delay')
    def test_complete_password_reset_flow(self, mock_task):
        """Test complete password reset email flow."""
        # Setup
        mock_task.return_value = Mock(id="task_456")
        
        user = self.users[0]
        # Mock the user method directly on the instance
        user.get_password_reset_url = Mock(return_value="http://example.com/reset/456")
        
        # Execute
        send_password_reset_email(user)
        
        # Verify task was called with correct parameters
        mock_task.assert_called_once()
        call_args = mock_task.call_args[1]
        
        self.assertEqual(call_args['to'], user.email)
        self.assertEqual(call_args['subject'], "Reset your password")
        self.assertIn("http://example.com/reset/456", call_args['contents'])
        
        # Verify user method was called
        user.get_password_reset_url.assert_called_once()

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_email_task_with_account_rotation(self, mock_smtp_class):
        """Test email task with account rotation."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp

        # Execute multiple tasks to test rotation
        for i in range(3):
            send_email_task(
                to=f"user{i}@example.com",
                subject=f"Test Subject {i}",
                contents=f"Test content {i}",
            )

        # Verify SMTP was called multiple times
        self.assertEqual(mock_smtp_class.call_count, 3)
        self.assertEqual(mock_smtp.send.call_count, 3)

        # Verify account rotation by checking the oauth2_file parameter
        smtp_calls = mock_smtp_class.call_args_list
        oauth_files = [call[1]["oauth2_file"] for call in smtp_calls]
        self.assertIn("/path/to/oauth1.json", oauth_files)
        self.assertIn("/path/to/oauth2.json", oauth_files)

    @patch("apps.emails.services.send_email_task.delay")
    def test_adapter_integration_with_services(self, mock_task):
        """Test CustomAccountAdapter integration with email services."""
        # Setup
        adapter = CustomAccountAdapter()
        mock_task.return_value = Mock(id="adapter_task")
        user = self.users[0]

        # Test adapter send_mail
        adapter.send_mail(
            template_prefix="account/email/signup_confirmation",
            email=user.email,
            context={"user": user},
        )

        # Verify task was called
        mock_task.assert_called_once()
        call_args = mock_task.call_args[1]
        self.assertEqual(call_args["to"], user.email)

    @override_settings(GMAIL_ACCOUNTS=[])
    def test_missing_gmail_accounts_configuration(self):
        """Test error handling when no Gmail accounts are configured."""
        with self.assertRaises(ImproperlyConfigured) as context:
            send_email_task(
                to="test@example.com", subject="Test Subject", contents="Test content"
            )

        self.assertIn("No Gmail accounts configured", str(context.exception))

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"}
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_error_handling_integration(self, mock_smtp_class):
        """Test error handling across the email flow."""
        # Setup SMTP to raise exception
        mock_smtp_class.side_effect = Exception("SMTP connection failed")

        # Execute task and expect it to handle the error
        with self.assertLogs("emails", level="ERROR") as log:
            send_email_task(
                to="test@example.com", subject="Test Subject", contents="Test content"
            )

        # Verify error was logged
        self.assertTrue(
            any("Failed to send email" in message for message in log.output)
        )

    @patch("apps.emails.services.send_email_task.delay")
    def test_multiple_email_types_integration(self, mock_task):
        """Test sending multiple types of emails."""
        # Setup
        mock_task.return_value = Mock(id="multi_task")
        
        user = self.users[0]
        # Mock the user methods directly on the instance
        user.get_confirmation_url = Mock(return_value="http://example.com/confirm/123")
        user.get_password_reset_url = Mock(return_value="http://example.com/reset/456")
        
        # Send both types of emails
        send_signup_confirmation_email(user)
        send_password_reset_email(user)
        
        # Verify both tasks were called
        self.assertEqual(mock_task.call_count, 2)
        
        # Get all call arguments
        calls = mock_task.call_args_list
        
        # Verify first call (confirmation email)
        confirm_call = calls[0][1]
        self.assertEqual(confirm_call['to'], user.email)
        self.assertEqual(confirm_call['subject'], "Confirm your email address")
        self.assertIn("http://example.com/confirm/123", confirm_call['contents'])
        
        # Verify second call (password reset email)
        reset_call = calls[1][1]
        self.assertEqual(reset_call['to'], user.email)
        self.assertEqual(reset_call['subject'], "Reset your password")
        self.assertIn("http://example.com/reset/456", reset_call['contents'])
        
        # Verify user methods were called
        user.get_confirmation_url.assert_called_once()
        user.get_password_reset_url.assert_called_once()


@pytest.mark.integration
class TestEmailCacheIntegration(TestCase):
    """
    Test email caching integration and account rotation.

    This test class focuses on:
    - Account index caching behavior
    - Cache error handling and fallbacks
    - Cache initialization scenarios
    - Account rotation across multiple requests
    """

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_account_index_caching(self, mock_smtp_class):
        """Test account index caching across multiple task calls."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp

        # Execute multiple tasks
        for i in range(4):
            send_email_task(
                to=f"user{i}@example.com",
                subject=f"Test Subject {i}",
                contents=f"Test content {i}",
            )

        # Verify cache was used for account rotation
        # Should cycle through accounts: 0, 1, 0, 1
        self.assertEqual(mock_smtp_class.call_count, 4)

        # Verify account rotation pattern
        smtp_calls = mock_smtp_class.call_args_list
        oauth_files = [call[1]["oauth2_file"] for call in smtp_calls]
        # Should alternate between the two oauth files
        self.assertEqual(len(set(oauth_files)), 2)  # Two different files used

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"}
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("django.core.cache.cache.incr")
    @patch("django.core.cache.cache.set")
    def test_cache_error_handling(
        self, mock_cache_set, mock_cache_incr, mock_smtp_class
    ):
        """Test cache error handling in email tasks."""
        # Setup cache.incr to raise ValueError (key not found)
        # and cache.set to work normally for fallback
        mock_cache_incr.side_effect = ValueError("Key not found")
        mock_cache_set.return_value = True
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp

        # Execute task - should still work despite cache errors
        send_email_task(
            to="test@example.com", subject="Test Subject", contents="Test content"
        )

        # Verify email was still sent
        mock_smtp.send.assert_called_once()
        # Verify fallback cache.set was called
        mock_cache_set.assert_called_once_with("last_gmail_account_index", 1)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"}
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_cache_initialization(self, mock_smtp_class):
        """Test cache initialization when counter doesn't exist."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp

        # Clear cache to simulate first run
        cache.delete("last_gmail_account_index")

        # Execute task
        send_email_task(
            to="test@example.com", subject="Test Subject", contents="Test content"
        )

        # Verify email was sent and cache was initialized
        mock_smtp.send.assert_called_once()
        self.assertEqual(cache.get("last_gmail_account_index"), 1)


@pytest.mark.integration
class TestEmailTemplateIntegration(TestCase):
    """
    Test email template integration and rendering.
    """

    def setUp(self):
        """Set up test data."""
        self.users = [CustomUserFactory() for _ in range(3)]

    @patch("apps.emails.adapters.render_to_string")
    @patch("apps.emails.services.send_email_task.delay")
    def test_template_rendering_integration(self, mock_task, mock_render):
        """Test template rendering integration with email services."""
        # Setup
        mock_render.side_effect = [
            "Test Subject",  # Subject template
            "Test text content",  # Text template
            "<html>Test HTML content</html>",  # HTML template
        ]
        mock_task.return_value = Mock(id="template_task")
        user = self.users[0]

        # Create adapter and send email
        adapter = CustomAccountAdapter()
        adapter.send_mail(
            template_prefix="account/email/test",
            email=user.email,
            context={"user": user},
        )

        # Verify templates were rendered
        self.assertEqual(mock_render.call_count, 3)

        # Verify task was called with rendered content
        mock_task.assert_called_once()
        call_args = mock_task.call_args[1]
        self.assertEqual(call_args["to"], user.email)
        self.assertEqual(call_args["subject"], "Test Subject")
        self.assertEqual(call_args["contents"], "<html>Test HTML content</html>")

    @patch("apps.emails.adapters.render_to_string")
    @patch("apps.emails.services.send_email_task.delay")
    def test_template_error_handling_integration(self, mock_task, mock_render):
        """Test template error handling integration."""
        # Setup template rendering to fail
        mock_render.side_effect = Exception("Template not found")
        mock_task.return_value = Mock(id="error_task")
        user = self.users[0]

        # Create adapter and attempt to send email
        adapter = CustomAccountAdapter()

        # Should handle template errors gracefully
        with self.assertRaises(Exception):
            adapter.send_mail(
                template_prefix="account/email/nonexistent",
                email=user.email,
                context={"user": user},
            )


@pytest.mark.integration
class TestEmailValidationIntegration(TestCase):
    """
    Test email validation and edge cases in integration scenarios.
    """

    def setUp(self):
        """Set up test data."""
        self.users = [CustomUserFactory() for _ in range(3)]

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"}
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_error_handling_integration(self, mock_smtp_class):
        """Test error handling in email integration."""
        # Setup SMTP to raise exception
        mock_smtp = Mock()
        mock_smtp.send.side_effect = Exception("SMTP connection failed")
        mock_smtp_class.return_value = mock_smtp
        
        # Test that exception is properly handled and logged
        with self.assertLogs('emails', level='ERROR') as log:
            # Task should handle the exception gracefully and not re-raise it
            send_email_task(
                to="test@example.com",
                subject="Test Subject", 
                contents="Test content"
            )
        
        # Verify error was logged
        self.assertTrue(any('Failed to send email' in record.getMessage()
                           for record in log.records))

    @patch("apps.emails.services.send_email_task.delay")
    def test_email_validation_integration(self, mock_task):
        """Test email validation in integration flow."""
        mock_task.return_value = Mock(id="validation_task")

        # Test with valid email
        user = self.users[0]
        user.email = "valid@example.com"
        # Mock the user method
        user.get_confirmation_url = Mock(return_value="http://example.com/confirm/123")
        
        send_signup_confirmation_email(user)

        # Verify email was sent
        mock_task.assert_called_once()
        call_args = mock_task.call_args[1]
        self.assertEqual(call_args["to"], "valid@example.com")

        # Reset mock for next test
        mock_task.reset_mock()

        # Test with edge case email formats
        edge_case_emails = [
            "user+tag@example.com",
            "user.name@example.co.uk",
            "123@example.com",
        ]

        for email in edge_case_emails:
            user.email = email
            # Mock the user method for each iteration
            user.get_confirmation_url = Mock(return_value="http://example.com/confirm/123")
            
            send_signup_confirmation_email(user)

            call_args = mock_task.call_args[1]
            self.assertEqual(call_args["to"], email)
            mock_task.reset_mock()

    @override_settings(GMAIL_ACCOUNTS=[])
    def test_empty_gmail_accounts_integration(self):
        """Test integration behavior with empty Gmail accounts configuration."""
        with self.assertRaises(ImproperlyConfigured):
            send_email_task(
                to="user@example.com", subject="Test Subject", contents="Test content"
            )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.cache")
    def test_cache_integration_edge_cases(self, mock_cache, mock_smtp_class):
        """Test cache integration edge cases."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp

        # Test cache increment failure
        mock_cache.incr.side_effect = ValueError("Key not found")
        mock_cache.set.return_value = True

        # Should still work with cache error (fallback to index 1)
        send_email_task(
            to="user@example.com", subject="Test Subject", contents="Test content"
        )

        # Verify email was sent despite cache error
        mock_smtp.send.assert_called_once()
        mock_cache.set.assert_called_once_with("last_gmail_account_index", 1)

    @patch('apps.emails.services.send_email_task.delay')
    def test_user_method_integration(self, mock_task):
        """Test integration with user model methods."""
        mock_task.return_value = Mock(id="user_method_task")
        
        user = self.users[0]
        # Mock the user methods directly on the instance
        user.get_confirmation_url = Mock(return_value="http://example.com/confirm/abc123")
        user.get_password_reset_url = Mock(return_value="http://example.com/reset/def456")
        
        # Test confirmation email
        send_signup_confirmation_email(user)
        user.get_confirmation_url.assert_called_once()
        
        # Test password reset email
        send_password_reset_email(user)
        user.get_password_reset_url.assert_called_once()
        
        # Verify both tasks were called
        self.assertEqual(mock_task.call_count, 2)
        
        # Verify URLs are included in email contents
        calls = mock_task.call_args_list
        confirm_contents = calls[0][1]['contents']
        reset_contents = calls[1][1]['contents']
        
        self.assertIn("http://example.com/confirm/abc123", confirm_contents)
        self.assertIn("http://example.com/reset/def456", reset_contents)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_email_timeout_handling(self, mock_smtp_class):
        """Test email timeout handling in integration scenarios."""
        # Setup SMTP to raise timeout exception
        mock_smtp = Mock()
        mock_smtp.send.side_effect = TimeoutError("Connection timeout")
        mock_smtp_class.return_value = mock_smtp

        # Test that timeout is handled gracefully and logged
        with self.assertLogs('emails', level='ERROR') as log:
            send_email_task(
                to="user@example.com", subject="Test Subject", contents="Test content"
            )

        # Verify SMTP was attempted
        mock_smtp.send.assert_called_once()
        
        # Verify timeout error was logged
        self.assertTrue(any('Failed to send email' in record.getMessage()
                           for record in log.records))
