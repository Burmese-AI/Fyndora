"""
Performance and system tests for the email services.

Following the test plan: Email Services (apps.emails)
- Performance tests for bulk email sending
- System tests for email delivery under load
- Load testing for Gmail account rotation
- Concurrent email processing tests
"""

import threading
import time
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, TransactionTestCase, override_settings

from apps.emails.services import (
    send_signup_confirmation_email,
    send_password_reset_email,
)
from apps.emails.tasks import send_email_task
from tests.factories.user_factories import CustomUserFactory


@pytest.mark.performance
class TestEmailPerformance(TestCase):
    """Test email performance under various loads."""

    def setUp(self):
        """Set up test data."""
        self.users = [CustomUserFactory() for _ in range(10)]

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.services.send_email_task.delay")
    def test_bulk_email_performance(self, mock_task, mock_smtp_class):
        """Test bulk email sending performance."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_task.return_value = Mock(id="bulk_task")

        start_time = time.time()

        # Send emails to multiple users
        for user in self.users:
            # Mock the user method
            user.get_confirmation_url = Mock(
                return_value="http://example.com/confirm/123"
            )
            send_signup_confirmation_email(user)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / len(self.users)

        # Performance assertions
        self.assertLess(avg_time_per_email, 0.1)  # Less than 100ms per email
        self.assertLess(total_time, 2.0)  # Total time under 2 seconds

        # Verify all emails were queued
        self.assertEqual(mock_task.call_count, len(self.users))

        # Verify each call had correct user email
        calls = mock_task.call_args_list
        sent_emails = [call[1]["to"] for call in calls]
        expected_emails = [user.email for user in self.users]

        for email in expected_emails:
            self.assertIn(email, sent_emails)

        # Verify all calls used correct subject
        subjects = [call[1]["subject"] for call in calls]
        for subject in subjects:
            self.assertEqual(subject, "Confirm your email address")

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": f"test{i}@gmail.com", "oauth2_file": f"/path/to/oauth{i}.json"}
            for i in range(10)
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_large_account_pool_performance(self, mock_smtp_class):
        """Test performance with large Gmail account pool."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp

        start_time = time.time()

        # Send multiple emails to test account rotation
        for i in range(50):
            send_email_task(
                to=f"user{i}@example.com",
                subject=f"Test Subject {i}",
                contents=f"Test content {i}",
            )

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / 50

        # Performance assertions
        self.assertLess(avg_time_per_email, 0.2)  # Less than 200ms per email
        self.assertLess(total_time, 10.0)  # Total time under 10 seconds

        # Verify all emails were sent
        self.assertEqual(mock_smtp.send.call_count, 50)

        # Verify account rotation across the large pool
        smtp_calls = mock_smtp_class.call_args_list
        oauth_files = [call[1]["oauth2_file"] for call in smtp_calls]
        unique_files = set(oauth_files)
        # Should use multiple different oauth files from the pool
        self.assertGreater(len(unique_files), 1)

    @patch("apps.emails.services.send_email_task.delay")
    def test_concurrent_email_performance(self, mock_task):
        """Test performance of concurrent email requests."""
        # Setup
        mock_task.return_value = Mock(id="concurrent_task")
        results = []
        errors = []

        def send_email_for_user(user):
            try:
                start_time = time.time()
                # Mock the user method
                user.get_confirmation_url = Mock(
                    return_value="http://example.com/confirm/123"
                )
                send_signup_confirmation_email(user)
                end_time = time.time()
                results.append(
                    {"user": user.email, "time": end_time - start_time, "success": True}
                )
            except Exception as e:
                errors.append(f"Error for {user.email}: {e}")

        # Create and start threads
        threads = []
        overall_start = time.time()

        for user in self.users:
            thread = threading.Thread(target=send_email_for_user, args=(user,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)  # Add timeout to prevent hanging

        overall_end = time.time()
        total_concurrent_time = overall_end - overall_start

        # Performance assertions
        self.assertLess(total_concurrent_time, 3.0)  # Should complete within 3 seconds
        self.assertEqual(len(results), len(self.users))
        self.assertEqual(len(errors), 0)

        # Check individual email times
        individual_times = [result["time"] for result in results]
        max_individual_time = max(individual_times)
        avg_individual_time = sum(individual_times) / len(individual_times)

        self.assertLess(max_individual_time, 1.0)  # No single email should take > 1s
        self.assertLess(avg_individual_time, 0.5)  # Average should be < 500ms

        # Verify all emails were queued
        self.assertEqual(mock_task.call_count, len(self.users))

        # Verify thread safety - all users should have been processed
        calls = mock_task.call_args_list
        sent_emails = [call[1]["to"] for call in calls]
        expected_emails = [user.email for user in self.users]

        for email in expected_emails:
            self.assertIn(email, sent_emails)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    def test_email_task_execution_performance(self, mock_smtp_class):
        """Test direct email task execution performance."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp

        # Test single email performance
        start_time = time.time()

        send_email_task(
            to="performance@example.com",
            subject="Performance Test",
            contents="This is a performance test email.",
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # Performance assertions
        self.assertLess(execution_time, 1.0)  # Should complete within 1 second
        mock_smtp.send.assert_called_once()

        # Test multiple sequential emails
        mock_smtp.reset_mock()
        start_time = time.time()

        for i in range(20):
            send_email_task(
                to=f"perf{i}@example.com",
                subject=f"Performance Test {i}",
                contents=f"This is performance test email {i}.",
            )

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / 20

        # Performance assertions for batch
        self.assertLess(avg_time_per_email, 0.1)  # Less than 100ms per email
        self.assertLess(total_time, 5.0)  # Total time under 5 seconds
        self.assertEqual(mock_smtp.send.call_count, 20)


@pytest.mark.performance
class TestEmailCachePerformance(TestCase):
    """Test email caching performance and account rotation efficiency."""

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": f"test{i}@gmail.com", "oauth2_file": f"/path/to/oauth{i}.json"}
            for i in range(20)
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.cache")
    def test_cache_rotation_performance(self, mock_cache, mock_smtp_class):
        """Test performance of cache-based account rotation."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_cache.incr.side_effect = lambda key, delta=1: (lambda x: x % 20)(
            mock_cache.incr.call_count
        )

        start_time = time.time()

        # Send many emails to test rotation performance
        for i in range(100):
            send_email_task(
                to=f"cache_perf{i}@example.com",
                subject=f"Cache Performance Test {i}",
                contents=f"Cache performance test content {i}.",
            )

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / 100

        # Performance assertions
        self.assertLess(avg_time_per_email, 0.05)  # Less than 50ms per email
        self.assertLess(total_time, 8.0)  # Total time under 8 seconds

        # Verify cache was used efficiently
        self.assertEqual(mock_cache.incr.call_count, 100)
        self.assertEqual(mock_smtp.send.call_count, 100)

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.cache")
    def test_cache_error_fallback_performance(self, mock_cache, mock_smtp_class):
        """Test performance when cache operations fail."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_cache.incr.side_effect = ValueError("Key not found")
        mock_cache.set.return_value = True

        start_time = time.time()

        # Send emails with cache errors
        for i in range(10):
            send_email_task(
                to=f"cache_error{i}@example.com",
                subject=f"Cache Error Test {i}",
                contents=f"Cache error test content {i}.",
            )

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / 10

        # Performance should not degrade significantly with cache errors
        self.assertLess(avg_time_per_email, 0.2)  # Less than 200ms per email
        self.assertLess(total_time, 3.0)  # Total time under 3 seconds

        # Verify fallback behavior
        self.assertEqual(mock_smtp.send.call_count, 10)
        self.assertEqual(mock_cache.set.call_count, 10)  # Should try to reset cache


@pytest.mark.system
class TestEmailSystemWorkflows(TransactionTestCase):
    """System tests for complete email workflows."""

    def setUp(self):
        """Set up test data."""
        self.users = [CustomUserFactory() for _ in range(5)]

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.services.send_email_task.delay")
    def test_complete_email_system_workflow(self, mock_task, mock_smtp_class):
        """Test complete email system workflow from user action to delivery."""
        # Setup
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_task.return_value = Mock(id="system_task")

        user = self.users[0]
        user.get_confirmation_url = Mock(return_value="http://example.com/confirm/123")
        user.get_password_reset_url = Mock(return_value="http://example.com/reset/456")

        # 1. User signup confirmation workflow
        send_signup_confirmation_email(user)

        # Verify service layer
        mock_task.assert_called_once()
        signup_call = mock_task.call_args[1]
        self.assertEqual(signup_call["to"], user.email)
        self.assertEqual(signup_call["subject"], "Confirm your email address")
        self.assertIn("http://example.com/confirm/123", signup_call["contents"])

        # Reset for next test
        mock_task.reset_mock()

        # 2. Password reset workflow
        send_password_reset_email(user)

        # Verify service layer
        mock_task.assert_called_once()
        reset_call = mock_task.call_args[1]
        self.assertEqual(reset_call["to"], user.email)
        self.assertEqual(reset_call["subject"], "Reset your password")
        self.assertIn("http://example.com/reset/456", reset_call["contents"])

        # 3. Verify user methods were called
        user.get_confirmation_url.assert_called_once()
        user.get_password_reset_url.assert_called_once()

    @override_settings(GMAIL_ACCOUNTS=[])
    def test_email_system_error_handling(self):
        """Test system-level error handling for email configuration."""
        user = self.users[0]

        # Test missing configuration
        with self.assertRaises(ImproperlyConfigured):
            send_email_task(
                to=user.email, subject="Test Subject", contents="Test content"
            )

    @patch("apps.emails.services.send_email_task.delay")
    def test_email_service_reliability_system(self, mock_task):
        """Test email service reliability under system conditions."""
        # Test with different task return values
        mock_task.side_effect = [
            Mock(id="task_1"),
            Mock(id="task_2"),
            Exception("Temporary failure"),
            Mock(id="task_4"),
        ]

        # Send emails with mixed success/failure
        successful_sends = 0
        failed_sends = 0

        for i, user in enumerate(self.users[:4]):
            try:
                # Mock the user method
                user.get_confirmation_url = Mock(
                    return_value="http://example.com/confirm/123"
                )
                send_signup_confirmation_email(user)
                successful_sends += 1
            except Exception:
                failed_sends += 1

        # Verify that failures are handled gracefully at system level
        self.assertEqual(mock_task.call_count, 4)
        self.assertGreater(successful_sends, 0)  # At least some should succeed
        self.assertLess(failed_sends, 4)  # Not all should fail
