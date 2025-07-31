"""
Unit tests for Email background tasks and Celery integration.

Tests advanced scenarios, error handling, and task behavior.
"""

from unittest.mock import Mock, patch

from django.conf import settings
import pytest
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.emails.tasks import send_email_task
from tests.factories import CustomUserFactory


@pytest.mark.unit
class TestEmailTasksAdvanced(TestCase):
    """Test advanced email task scenarios."""

    def setUp(self):
        """Set up test data."""
        self.test_email = "test@example.com"
        self.test_subject = "Test Subject"
        self.test_contents = "Test email contents"
        cache.clear()

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_send_email_task_oauth_file_parameter(self, mock_yagmail_smtp):
        """Test that OAuth file parameter is correctly passed."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        send_email_task(self.test_email, self.test_subject, self.test_contents)

        # Verify OAuth file is passed correctly
        mock_yagmail_smtp.assert_called_once_with(
            "test1@gmail.com", oauth2_file="/path/to/oauth1.json"
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_send_email_task_single_account_no_rotation(self, mock_yagmail_smtp):
        """Test that single account doesn't cause rotation issues."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # Send multiple emails
        for i in range(5):
            send_email_task(
                f"test{i}@example.com", self.test_subject, self.test_contents
            )

        # All should use the same account
        for call in mock_yagmail_smtp.call_args_list:
            self.assertEqual(call[0][0], "test@gmail.com")
            self.assertEqual(call[1]["oauth2_file"], "/path/to/oauth.json")

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.cache")
    def test_send_email_task_cache_error_handling(self, mock_cache, mock_yagmail_smtp):
        """Test handling of cache errors during account selection."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # Mock cache.incr to raise ValueError (key doesn't exist)
        mock_cache.incr.side_effect = ValueError("Key does not exist")
        mock_cache.set.return_value = None

        send_email_task(self.test_email, self.test_subject, self.test_contents)

        # Should set cache and use first account
        mock_cache.set.assert_called_once_with("last_gmail_account_index", 1)
        mock_yagmail_smtp.assert_called_once_with(
            "test1@gmail.com", oauth2_file="/path/to/oauth1.json"
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.logger")
    def test_send_email_task_yagmail_import_error(self, mock_logger, mock_yagmail_smtp):
        """Test handling of yagmail import or initialization errors."""
        mock_yagmail_smtp.side_effect = ImportError("yagmail not installed")

        with self.assertRaises(ImportError):
            send_email_task(self.test_email, self.test_subject, self.test_contents)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.logger")
    def test_send_email_task_oauth_file_error(self, mock_logger, mock_yagmail_smtp):
        """Test handling of OAuth file errors."""
        mock_yagmail_smtp.side_effect = FileNotFoundError("OAuth file not found")

        with self.assertRaises(FileNotFoundError):
            send_email_task(self.test_email, self.test_subject, self.test_contents)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_send_email_task_email_parameters(self, mock_yagmail_smtp):
        """Test that email parameters are correctly passed to yagmail."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        custom_email = "custom@example.com"
        custom_subject = "Custom Subject with Special Characters: àáâã"
        custom_contents = "Custom contents with\nmultiple lines\nand special chars: €£¥"

        send_email_task(custom_email, custom_subject, custom_contents)

        mock_yag.send.assert_called_once_with(
            to=custom_email,
            subject=custom_subject,
            contents=custom_contents,
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_send_email_task_unicode_handling(self, mock_yagmail_smtp):
        """Test handling of Unicode characters in email content."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        unicode_email = "tëst@éxample.com"
        unicode_subject = "Tëst Sübject with Ünicöde"
        unicode_contents = "Tëst cöntents with émojis: 🚀📧✨"

        send_email_task(unicode_email, unicode_subject, unicode_contents)

        mock_yag.send.assert_called_once_with(
            to=unicode_email,
            subject=unicode_subject,
            contents=unicode_contents,
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.logger")
    def test_send_email_task_network_timeout(self, mock_logger, mock_yagmail_smtp):
        """Test handling of network timeout errors."""
        mock_yag = Mock()
        mock_yag.send.side_effect = TimeoutError("Network timeout")
        mock_yagmail_smtp.return_value = mock_yag

        send_email_task(self.test_email, self.test_subject, self.test_contents)

        mock_logger.exception.assert_called_once_with(
            f"Failed to send email to {self.test_email} from test@gmail.com."
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.logger")
    def test_send_email_task_authentication_error(self, mock_logger, mock_yagmail_smtp):
        """Test handling of authentication errors."""
        mock_yag = Mock()
        mock_yag.send.side_effect = Exception("Authentication failed")
        mock_yagmail_smtp.return_value = mock_yag

        send_email_task(self.test_email, self.test_subject, self.test_contents)

        mock_logger.exception.assert_called_once_with(
            f"Failed to send email to {self.test_email} from test@gmail.com."
        )


@pytest.mark.unit
class TestEmailTasksConfiguration(TestCase):
    """Test email tasks with different configuration scenarios."""

    def setUp(self):
        """Set up test data."""
        self.test_email = "test@example.com"
        self.test_subject = "Test Subject"
        self.test_contents = "Test email contents"
        cache.clear()

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com"},  # Missing oauth2_file
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_send_email_task_missing_oauth_file_config(self, mock_yagmail_smtp):
        """Test handling of missing oauth2_file in configuration."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # This should still work, yagmail will handle missing oauth2_file
        send_email_task(self.test_email, self.test_subject, self.test_contents)

        # Should call with None for oauth2_file
        mock_yagmail_smtp.assert_called_once_with("test1@gmail.com", oauth2_file=None)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {},  # Empty account config
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_send_email_task_empty_account_config(self, mock_yagmail_smtp):
        """Test handling of empty account configuration."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # Should use the empty config first (round-robin)
        send_email_task(self.test_email, self.test_subject, self.test_contents)

        mock_yagmail_smtp.assert_called_once_with(
            None,  # user will be None
            oauth2_file=None,
        )

    @override_settings()  # No GMAIL_ACCOUNTS setting at all
    def test_send_email_task_no_setting(self):
        """Test handling when GMAIL_ACCOUNTS setting doesn't exist."""
        # Actually remove the setting to test AttributeError
        if hasattr(settings, 'GMAIL_ACCOUNTS'):
            delattr(settings, 'GMAIL_ACCOUNTS')
        
        with self.assertRaises(AttributeError):
            send_email_task(self.test_email, self.test_subject, self.test_contents)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
            {"user": "test3@gmail.com", "oauth2_file": "/path/to/oauth3.json"},
            {"user": "test4@gmail.com", "oauth2_file": "/path/to/oauth4.json"},
            {"user": "test5@gmail.com", "oauth2_file": "/path/to/oauth5.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_send_email_task_large_account_pool(self, mock_yagmail_smtp):
        """Test round-robin with larger pool of accounts."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        expected_accounts = [
            "test1@gmail.com",
            "test2@gmail.com",
            "test3@gmail.com",
            "test4@gmail.com",
            "test5@gmail.com",
            "test1@gmail.com",  # Wraps around
        ]

        for i, expected_account in enumerate(expected_accounts):
            send_email_task(
                f"test{i}@example.com", self.test_subject, self.test_contents
            )

            # Get the last call
            last_call = mock_yagmail_smtp.call_args_list[-1]
            self.assertEqual(last_call[0][0], expected_account)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.cache")
    def test_send_email_task_cache_persistence(self, mock_cache, mock_yagmail_smtp):
        """Test that cache counter persists across task calls."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # Mock cache to return incrementing values
        mock_cache.incr.side_effect = [1, 2, 3, 4, 5]

        for i in range(5):
            send_email_task(
                f"test{i}@example.com", self.test_subject, self.test_contents
            )

        # Verify cache.incr was called 5 times
        self.assertEqual(mock_cache.incr.call_count, 5)
        for call in mock_cache.incr.call_args_list:
            self.assertEqual(call[0][0], "last_gmail_account_index")


@pytest.mark.unit
class TestEmailTasksIntegration(TestCase):
    """Test email tasks integration with other components."""

    def setUp(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        cache.clear()

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.services.send_email_task.delay")
    def test_email_services_task_integration(self, mock_delay, mock_yagmail_smtp):
        """Test integration between email services and tasks."""
        from apps.emails.services import send_signup_confirmation_email

        # Mock user methods
        self.user.get_confirmation_url = Mock(
            return_value="http://example.com/confirm/123"
        )

        send_signup_confirmation_email(self.user)

        mock_delay.assert_called_once_with(
            to=self.user.email,
            subject="Confirm your email address",
            contents=f"Please confirm your email address by clicking this link: {self.user.get_confirmation_url()}",
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_email_task_with_real_user_data(self, mock_yagmail_smtp):
        """Test email task with real user factory data."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        send_email_task(
            to=self.user.email,
            subject="Welcome to our platform",
            contents=f"Hello {self.user.username}, welcome to our platform!",
        )

        mock_yag.send.assert_called_once_with(
            to=self.user.email,
            subject="Welcome to our platform",
            contents=f"Hello {self.user.username}, welcome to our platform!",
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.logger")
    def test_email_task_logging_with_user_data(self, mock_logger, mock_yagmail_smtp):
        """Test email task logging includes user-specific information."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        send_email_task(
            to=self.user.email, subject="Test Subject", contents="Test contents"
        )

        mock_logger.info.assert_called_once_with(
            f"Email sent successfully to {self.user.email} from test@gmail.com."
        )
