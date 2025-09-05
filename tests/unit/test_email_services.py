"""
Unit tests for Email services and background tasks.

Tests email service functions, Celery tasks, and email adapters.
"""

from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist
from django.test import TestCase, override_settings

from apps.emails.adapters import CustomAccountAdapter
from apps.emails.services import (
    send_password_reset_email,
    send_signup_confirmation_email,
)
from apps.emails.tasks import send_email_task
from tests.factories import CustomUserFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestEmailServices(TestCase):
    """Test email service functions."""

    def setUp(self):
        """Set up test data."""
        self.user = CustomUserFactory()
        # Mock the user methods that don't exist yet
        self.user.get_confirmation_url = Mock(
            return_value="http://example.com/confirm/123"
        )
        self.user.get_password_reset_url = Mock(
            return_value="http://example.com/reset/456"
        )

    @patch("apps.emails.services.send_email_task.delay")
    def test_send_signup_confirmation_email(self, mock_send_email_task):
        """Test sending signup confirmation email."""
        send_signup_confirmation_email(self.user)

        mock_send_email_task.assert_called_once_with(
            to=self.user.email,
            subject="Confirm your email address",
            contents=f"Please confirm your email address by clicking this link: {self.user.get_confirmation_url()}",
        )

    @patch("apps.emails.services.send_email_task.delay")
    def test_send_password_reset_email(self, mock_send_email_task):
        """Test sending password reset email."""
        send_password_reset_email(self.user)

        mock_send_email_task.assert_called_once_with(
            to=self.user.email,
            subject="Reset your password",
            contents=f"Please reset your password by clicking this link: {self.user.get_password_reset_url()}",
        )

    @patch("apps.emails.services.send_email_task.delay")
    def test_send_signup_confirmation_email_calls_user_method(
        self, mock_send_email_task
    ):
        """Test that signup confirmation email calls user's get_confirmation_url method."""
        send_signup_confirmation_email(self.user)

        self.user.get_confirmation_url.assert_called_once()

    @patch("apps.emails.services.send_email_task.delay")
    def test_send_password_reset_email_calls_user_method(self, mock_send_email_task):
        """Test that password reset email calls user's get_password_reset_url method."""
        send_password_reset_email(self.user)

        self.user.get_password_reset_url.assert_called_once()


@pytest.mark.unit
class TestEmailTasks(TestCase):
    """Test email background tasks."""

    def setUp(self):
        """Set up test data."""
        self.test_email = "test@example.com"
        self.test_subject = "Test Subject"
        self.test_contents = "Test email contents"

        # Clear cache before each test
        cache.clear()

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.logger")
    def test_send_email_task_success(self, mock_logger, mock_yagmail_smtp):
        """Test successful email sending."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        send_email_task(self.test_email, self.test_subject, self.test_contents)

        mock_yagmail_smtp.assert_called_once_with(
            "test1@gmail.com", oauth2_file="/path/to/oauth1.json"
        )
        mock_yag.send.assert_called_once_with(
            to=self.test_email,
            subject=self.test_subject,
            contents=self.test_contents,
        )
        mock_logger.info.assert_called_once_with(
            f"Email sent successfully to {self.test_email} from test1@gmail.com."
        )

    @override_settings(GMAIL_ACCOUNTS=[])
    def test_send_email_task_no_accounts_configured(self):
        """Test error when no Gmail accounts are configured."""
        with self.assertRaises(ImproperlyConfigured) as context:
            send_email_task(self.test_email, self.test_subject, self.test_contents)

        self.assertEqual(
            str(context.exception),
            "No Gmail accounts configured in settings.GMAIL_ACCOUNTS",
        )

    @override_settings(GMAIL_ACCOUNTS=None)
    @patch("apps.emails.tasks.logger")
    def test_send_email_task_none_accounts_configured(self, mock_logger):
        """Test critical log when GMAIL_ACCOUNTS is None."""
        with self.assertRaises(ImproperlyConfigured):
            send_email_task(self.test_email, self.test_subject, self.test_contents)

        mock_logger.critical.assert_called_once_with(
            "CRITICAL: No Gmail accounts are configured in settings.GMAIL_ACCOUNTS."
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
            {"user": "test3@gmail.com", "oauth2_file": "/path/to/oauth3.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.cache")
    def test_send_email_task_round_robin_selection(self, mock_cache, mock_yagmail_smtp):
        """Test round-robin account selection."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # Mock cache.incr() to return specific values for round-robin testing
        mock_cache.incr.side_effect = [1, 2, 3, 4]  # Will be called 4 times

        # First call should use first account (index 0)
        # cache.incr() returns 1, then (1-1) % 3 = 0
        send_email_task(self.test_email, self.test_subject, self.test_contents)
        first_call = mock_yagmail_smtp.call_args

        # Second call should use second account (index 1)
        # cache.incr() returns 2, then (2-1) % 3 = 1
        send_email_task(self.test_email, self.test_subject, self.test_contents)
        second_call = mock_yagmail_smtp.call_args

        # Third call should use third account (index 2)
        # cache.incr() returns 3, then (3-1) % 3 = 2
        send_email_task(self.test_email, self.test_subject, self.test_contents)
        third_call = mock_yagmail_smtp.call_args

        # Fourth call should wrap around to first account (index 0)
        # cache.incr() returns 4, then (4-1) % 3 = 0
        send_email_task(self.test_email, self.test_subject, self.test_contents)
        fourth_call = mock_yagmail_smtp.call_args

        # Verify round-robin behavior
        self.assertEqual(first_call[0][0], "test1@gmail.com")
        self.assertEqual(second_call[0][0], "test2@gmail.com")
        self.assertEqual(third_call[0][0], "test3@gmail.com")
        self.assertEqual(fourth_call[0][0], "test1@gmail.com")

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test@gmail.com", "oauth2_file": "/path/to/oauth.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.logger")
    def test_send_email_task_exception_handling(self, mock_logger, mock_yagmail_smtp):
        """Test exception handling during email sending."""
        mock_yag = Mock()
        mock_yag.send.side_effect = Exception("SMTP connection failed")
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
    def test_send_email_task_cache_initialization(self, mock_yagmail_smtp):
        """Test cache initialization when counter doesn't exist."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # Ensure cache is clear
        cache.clear()

        send_email_task(self.test_email, self.test_subject, self.test_contents)

        # Should use first account when cache is initialized
        mock_yagmail_smtp.assert_called_once_with(
            "test@gmail.com", oauth2_file="/path/to/oauth.json"
        )

    @override_settings(
        GMAIL_ACCOUNTS=[
            {"user": "test1@gmail.com", "oauth2_file": "/path/to/oauth1.json"},
            {"user": "test2@gmail.com", "oauth2_file": "/path/to/oauth2.json"},
        ]
    )
    @patch("apps.emails.tasks.yagmail.SMTP")
    @patch("apps.emails.tasks.cache")
    def test_send_email_task_with_existing_cache_value(
        self, mock_cache, mock_yagmail_smtp
    ):
        """Test email task with existing cache value."""
        mock_yag = Mock()
        mock_yagmail_smtp.return_value = mock_yag

        # Mock cache.incr() to return 2, which will result in (2-1) % 2 = 1 (second account)
        mock_cache.incr.return_value = 2

        send_email_task(self.test_email, self.test_subject, self.test_contents)

        # The cache.incr() returns 2, then (2-1) % 2 = 1, which is index 1 (second account)
        mock_yagmail_smtp.assert_called_once_with(
            "test2@gmail.com", oauth2_file="/path/to/oauth2.json"
        )


@pytest.mark.unit
class TestSendInvitationEmail(TestCase):
    """Test send_invitation_email service function."""

    def setUp(self):
        """Set up test data."""
        from tests.factories.organization_factories import (
            OrganizationFactory,
            OrganizationMemberFactory,
        )
        from unittest.mock import Mock

        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(organization=self.organization)

        # Create a mock invitation object to avoid triggering signals
        self.invitation = Mock()
        self.invitation.organization = self.organization
        self.invitation.invited_by = self.org_member
        self.invitation.email = "invited@example.com"
        self.invitation.pk = "123"
        self.invitation.get_acceptance_url = Mock(
            return_value="/invitations/accept/123/"
        )

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @override_settings(DEBUG=True)
    def test_send_invitation_email_debug_mode(
        self, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email in DEBUG mode (covers lines 43-44)."""
        from apps.emails.services import send_invitation_email

        # Mock template rendering
        mock_render_to_string.side_effect = [
            "You're invited to join Test Organization\n",  # subject
            "<html><body>Invitation HTML</body></html>",  # html template
        ]

        send_invitation_email(self.invitation)

        # Verify email task was called with localhost:8000 domain
        mock_send_email_task.assert_called_once()
        call_args = mock_send_email_task.call_args
        self.assertEqual(call_args[1]["to"], "invited@example.com")
        self.assertEqual(
            call_args[1]["subject"], "You're invited to join Test Organization"
        )
        self.assertEqual(
            call_args[1]["contents"], "<html><body>Invitation HTML</body></html>"
        )

        # Verify context was passed correctly
        render_calls = mock_render_to_string.call_args_list
        self.assertEqual(len(render_calls), 2)

        # Check subject template call
        subject_call = render_calls[0]
        self.assertEqual(subject_call[0][0], "account/email/invitation_subject.txt")
        context = subject_call[0][1]
        self.assertEqual(context["invitation"], self.invitation)
        self.assertEqual(context["organization"], self.organization)
        self.assertEqual(context["invited_by"], self.org_member)
        self.assertEqual(
            context["acceptance_url"], "http://localhost:8000/invitations/accept/123/"
        )

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @patch("django.contrib.sites.models.Site.objects.get_current")
    @override_settings(DEBUG=False)
    def test_send_invitation_email_production_sites_framework(
        self, mock_get_current, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email in production with Sites framework (covers lines 47-55)."""
        from apps.emails.services import send_invitation_email

        # Mock Site.objects.get_current()
        mock_site = Mock()
        mock_site.domain = "example.com"
        mock_get_current.return_value = mock_site

        # Mock template rendering
        mock_render_to_string.side_effect = [
            "You're invited to join Test Organization\n",  # subject
            "<html><body>Invitation HTML</body></html>",  # html template
        ]

        send_invitation_email(self.invitation)

        # Verify email task was called with HTTPS protocol
        mock_send_email_task.assert_called_once()
        # call_args = mock_send_email_task.call_args

        # Check context for HTTPS URL
        render_calls = mock_render_to_string.call_args_list
        context = render_calls[0][0][1]
        self.assertEqual(
            context["acceptance_url"], "https://example.com/invitations/accept/123/"
        )

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @patch("django.contrib.sites.models.Site.objects.get_current")
    @override_settings(DEBUG=False, ALLOWED_HOSTS=["example.com", "localhost"])
    def test_send_invitation_email_sites_framework_fallback(
        self, mock_get_current, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email with Sites framework fallback (covers lines 56-60)."""
        from apps.emails.services import send_invitation_email

        # Mock Site.objects.get_current() to raise exception
        mock_get_current.side_effect = Exception("Site not found")

        # Mock template rendering
        mock_render_to_string.side_effect = [
            "You're invited to join Test Organization\n",  # subject
            "<html><body>Invitation HTML</body></html>",  # html template
        ]

        send_invitation_email(self.invitation)

        # Verify email task was called with ALLOWED_HOSTS fallback
        mock_send_email_task.assert_called_once()

        # Check context for HTTPS URL (first ALLOWED_HOST)
        render_calls = mock_render_to_string.call_args_list
        context = render_calls[0][0][1]
        self.assertEqual(
            context["acceptance_url"], "https://example.com/invitations/accept/123/"
        )

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @patch("django.contrib.sites.models.Site.objects.get_current")
    @override_settings(DEBUG=False, ALLOWED_HOSTS=["localhost"])
    def test_send_invitation_email_localhost_fallback(
        self, mock_get_current, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email with localhost fallback (covers lines 56-64)."""
        from apps.emails.services import send_invitation_email

        # Mock Site.objects.get_current() to raise exception
        mock_get_current.side_effect = Exception("Site not found")

        # Mock template rendering
        mock_render_to_string.side_effect = [
            "You're invited to join Test Organization\n",  # subject
            "<html><body>Invitation HTML</body></html>",  # html template
        ]

        send_invitation_email(self.invitation)

        # Verify email task was called with HTTP protocol for localhost
        mock_send_email_task.assert_called_once()

        # Check context for HTTP URL (localhost should use HTTP)
        render_calls = mock_render_to_string.call_args_list
        context = render_calls[0][0][1]
        self.assertEqual(
            context["acceptance_url"], "http://localhost/invitations/accept/123/"
        )

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @patch("django.contrib.sites.models.Site.objects.get_current")
    @override_settings(DEBUG=False, ALLOWED_HOSTS=[])
    def test_send_invitation_email_empty_allowed_hosts_fallback(
        self, mock_get_current, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email with empty ALLOWED_HOSTS fallback."""
        from apps.emails.services import send_invitation_email

        # Mock Site.objects.get_current() to raise exception
        mock_get_current.side_effect = Exception("Site not found")

        # Mock template rendering
        mock_render_to_string.side_effect = [
            "You're invited to join Test Organization\n",  # subject
            "<html><body>Invitation HTML</body></html>",  # html template
        ]

        send_invitation_email(self.invitation)

        # Verify email task was called with localhost fallback
        mock_send_email_task.assert_called_once()

        # Check context for localhost fallback
        render_calls = mock_render_to_string.call_args_list
        context = render_calls[0][0][1]
        self.assertEqual(
            context["acceptance_url"], "http://localhost/invitations/accept/123/"
        )

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @patch("apps.emails.services.logger")
    @override_settings(DEBUG=True)
    def test_send_invitation_email_html_template_fallback(
        self, mock_logger, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email with HTML template fallback to text (covers lines 85-92)."""
        from apps.emails.services import send_invitation_email
        from django.template import TemplateDoesNotExist

        # Mock template rendering - HTML template doesn't exist, fallback to text
        def side_effect(template_name, context):
            if template_name == "account/email/invitation_subject.txt":
                return "You're invited to join Test Organization\n"
            elif template_name == "account/email/invitation_message.html":
                raise TemplateDoesNotExist(template_name)
            elif template_name == "account/email/invitation_message.txt":
                return "Plain text invitation message"

        mock_render_to_string.side_effect = side_effect

        send_invitation_email(self.invitation)

        # Verify email task was called with text content
        mock_send_email_task.assert_called_once()
        call_args = mock_send_email_task.call_args
        self.assertEqual(call_args[1]["contents"], "Plain text invitation message")

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @patch("apps.emails.services.logger")
    @override_settings(DEBUG=True)
    def test_send_invitation_email_no_templates_found(
        self, mock_logger, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email when no templates are found (covers lines 88-92)."""
        from apps.emails.services import send_invitation_email
        from django.template import TemplateDoesNotExist

        # Mock template rendering - both HTML and text templates don't exist
        def side_effect(template_name, context):
            if template_name == "account/email/invitation_subject.txt":
                return "You're invited to join Test Organization\n"
            elif template_name == "account/email/invitation_message.html":
                raise TemplateDoesNotExist(template_name)
            elif template_name == "account/email/invitation_message.txt":
                raise TemplateDoesNotExist(template_name)

        mock_render_to_string.side_effect = side_effect

        send_invitation_email(self.invitation)

        # Verify error was logged and no email was sent
        mock_logger.error.assert_called_once_with(
            f"No invitation email templates found for invitation {self.invitation.pk}"
        )
        mock_send_email_task.assert_not_called()

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @patch("apps.emails.services.logger")
    @override_settings(DEBUG=True)
    def test_send_invitation_email_success_logging(
        self, mock_logger, mock_render_to_string, mock_send_email_task
    ):
        """Test send_invitation_email success logging."""
        from apps.emails.services import send_invitation_email

        # Mock template rendering
        mock_render_to_string.side_effect = [
            "You're invited to join Test Organization\n",  # subject
            "<html><body>Invitation HTML</body></html>",  # html template
        ]

        send_invitation_email(self.invitation)

        # Verify success was logged
        mock_logger.info.assert_called_once_with(
            f"Invitation email queued for {self.invitation.email} to join {self.invitation.organization.title}"
        )

    @patch("apps.emails.services.send_email_task.delay")
    @patch("apps.emails.services.render_to_string")
    @override_settings(DEBUG=True)
    def test_send_invitation_email_subject_newline_removal(
        self, mock_render_to_string, mock_send_email_task
    ):
        """Test that newlines are removed from email subject."""
        from apps.emails.services import send_invitation_email

        # Mock template rendering with multiline subject
        mock_render_to_string.side_effect = [
            "You're invited to join\nTest Organization\n\n",  # subject with newlines
            "<html><body>Invitation HTML</body></html>",  # html template
        ]

        send_invitation_email(self.invitation)

        # Verify subject has newlines removed
        mock_send_email_task.assert_called_once()
        call_args = mock_send_email_task.call_args
        self.assertEqual(
            call_args[1]["subject"], "You're invited to joinTest Organization"
        )


@pytest.mark.unit
class TestCustomAccountAdapter(TestCase):
    """Test custom account adapter for email sending."""

    def setUp(self):
        """Set up test data."""
        self.adapter = CustomAccountAdapter()
        self.test_email = "test@example.com"
        self.test_context = {"user": "testuser", "key": "testkey"}

    @patch("apps.emails.adapters.send_email_task.delay")
    @patch("apps.emails.adapters.render_to_string")
    def test_send_mail_with_html_template(
        self, mock_render_to_string, mock_send_email_task
    ):
        """Test sending mail with HTML template."""
        # Mock template rendering
        mock_render_to_string.side_effect = [
            "Test Subject\n",  # subject template
            "Test plain text body",  # text template
            "<html><body>Test HTML body</body></html>",  # html template
        ]

        self.adapter.send_mail("test_template", self.test_email, self.test_context)

        # Verify template rendering calls
        expected_calls = [
            (("test_template_subject.txt", self.test_context),),
            (("test_template_message.txt", self.test_context),),
            (("test_template_message.html", self.test_context),),
        ]
        self.assertEqual(mock_render_to_string.call_args_list, expected_calls)

        # Verify email task call
        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="Test Subject",  # newlines should be stripped
            contents="<html><body>Test HTML body</body></html>",
        )

    @patch("apps.emails.adapters.send_email_task.delay")
    @patch("apps.emails.adapters.render_to_string")
    def test_send_mail_without_html_template(
        self, mock_render_to_string, mock_send_email_task
    ):
        """Test sending mail when HTML template doesn't exist."""

        # Mock template rendering - HTML template raises TemplateDoesNotExist
        def side_effect(template_name, context):
            if template_name.endswith("_message.html"):
                raise TemplateDoesNotExist(template_name)
            elif template_name.endswith("_subject.txt"):
                return "Test Subject\n"
            elif template_name.endswith("_message.txt"):
                return "Test plain text body"

        mock_render_to_string.side_effect = side_effect

        self.adapter.send_mail("test_template", self.test_email, self.test_context)

        # Verify email task call with text content
        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="Test Subject",
            contents="Test plain text body",
        )

    @patch("apps.emails.adapters.send_email_task.delay")
    @patch("apps.emails.adapters.render_to_string")
    def test_send_mail_subject_newline_removal(
        self, mock_render_to_string, mock_send_email_task
    ):
        """Test that newlines are removed from email subject."""

        # Mock template rendering with multiline subject
        def side_effect(template_name, context):
            if template_name.endswith("_subject.txt"):
                return "Test Subject\nWith Multiple\nLines\n"
            elif template_name.endswith("_message.txt"):
                return "Test body"
            elif template_name.endswith("_message.html"):
                raise TemplateDoesNotExist(template_name)

        mock_render_to_string.side_effect = side_effect

        self.adapter.send_mail("test_template", self.test_email, self.test_context)

        # Verify subject has newlines removed
        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="Test SubjectWith MultipleLines",
            contents="Test body",
        )

    @patch("apps.emails.adapters.send_email_task.delay")
    @patch("apps.emails.adapters.render_to_string")
    def test_send_mail_template_context_passed(
        self, mock_render_to_string, mock_send_email_task
    ):
        """Test that template context is properly passed to render_to_string."""

        # Mock template rendering with proper side_effect function
        def side_effect(template_name, context):
            if template_name.endswith("_subject.txt"):
                return "Subject"
            elif template_name.endswith("_message.txt"):
                return "Body"
            elif template_name.endswith("_message.html"):
                raise TemplateDoesNotExist(template_name)

        mock_render_to_string.side_effect = side_effect

        custom_context = {"custom_key": "custom_value", "user": "testuser"}
        self.adapter.send_mail("custom_template", self.test_email, custom_context)

        # Verify context is passed to all template rendering calls
        for call_args in mock_render_to_string.call_args_list:
            if len(call_args[0]) > 1:  # If context is provided
                self.assertEqual(call_args[0][1], custom_context)

    @patch("apps.emails.adapters.send_email_task.delay")
    @patch("apps.emails.adapters.render_to_string")
    def test_send_mail_empty_html_content(
        self, mock_render_to_string, mock_send_email_task
    ):
        """Test sending mail when HTML template returns empty content."""
        mock_render_to_string.side_effect = [
            "Test Subject",  # subject
            "Test text body",  # text
            "",  # empty HTML
        ]

        self.adapter.send_mail("test_template", self.test_email, self.test_context)

        # Should fall back to text content when HTML is empty
        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="Test Subject",
            contents="Test text body",
        )
