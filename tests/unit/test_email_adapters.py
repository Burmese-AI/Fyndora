"""
Unit tests for Email adapters and template handling.

Tests custom account adapter functionality and template integration.
"""

import copy
from unittest.mock import Mock, patch
import pytest
from django.test import TestCase
from django.template import TemplateDoesNotExist

from apps.emails.adapters import CustomAccountAdapter
from tests.factories import CustomUserFactory


@pytest.mark.unit
class TestCustomAccountAdapterAdvanced(TestCase):
    """Test advanced custom account adapter scenarios."""

    def setUp(self):
        """Set up test data."""
        self.adapter = CustomAccountAdapter()
        self.test_email = "test@example.com"
        self.user = CustomUserFactory()
        self.test_context = {
            "user": self.user,
            "key": "activation_key_123",
            "site_name": "Test Site",
            "domain": "example.com",
        }

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_complex_context(self, mock_render_to_string, mock_send_email_task):
        """Test sending mail with complex context data."""
        mock_render_to_string.side_effect = [
            f"Welcome {self.user.username}!\n",
            f"Hello {self.user.username}, please activate your account.",
            f"<html><body><h1>Welcome {self.user.username}!</h1></body></html>",
        ]

        self.adapter.send_mail("activation", self.test_email, self.test_context)

        # Verify context is passed correctly
        for call_args in mock_render_to_string.call_args_list:
            self.assertEqual(call_args[0][1], self.test_context)

        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject=f"Welcome {self.user.username}!",
            contents=f"<html><body><h1>Welcome {self.user.username}!</h1></body></html>",
        )

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_template_prefix_variations(self, mock_render_to_string, mock_send_email_task):
        """Test different template prefix patterns."""
        test_cases = [
            "account/email/email_confirmation",
            "registration/activation",
            "password_reset",
            "welcome_email",
        ]

        for template_prefix in test_cases:
            with self.subTest(template_prefix=template_prefix):
                mock_render_to_string.reset_mock()
                mock_send_email_task.reset_mock()
                
                mock_render_to_string.side_effect = [
                    "Subject",
                    "Text body",
                    TemplateDoesNotExist("html template"),
                ]

                self.adapter.send_mail(template_prefix, self.test_email, self.test_context)

                # Verify correct template names are used
                expected_calls = [
                    f"{template_prefix}_subject.txt",
                    f"{template_prefix}_message.txt",
                    f"{template_prefix}_message.html",
                ]
                
                actual_calls = [call[0][0] for call in mock_render_to_string.call_args_list]
                self.assertEqual(actual_calls, expected_calls)

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_template_rendering_error(self, mock_render_to_string, mock_send_email_task):
        """Test handling of template rendering errors."""
        # Subject template fails
        mock_render_to_string.side_effect = Exception("Template syntax error")

        with self.assertRaises(Exception):
            self.adapter.send_mail("broken_template", self.test_email, self.test_context)

        # Email task should not be called if template rendering fails
        mock_send_email_task.assert_not_called()

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_text_template_missing(self, mock_render_to_string, mock_send_email_task):
        """Test handling when text template is missing."""
        def side_effect(template_name, context):
            if template_name.endswith("_subject.txt"):
                return "Test Subject"
            elif template_name.endswith("_message.txt"):
                raise TemplateDoesNotExist(template_name)
            elif template_name.endswith("_message.html"):
                return "<html><body>HTML content</body></html>"

        mock_render_to_string.side_effect = side_effect

        self.adapter.send_mail("signup_confirmation", self.test_email, self.test_context)

        # Should use HTML content when text template is missing
        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="Test Subject",
            contents="<html><body>HTML content</body></html>",
        )

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_both_templates_missing(self, mock_render_to_string, mock_send_email_task):
        """Test handling when both text and HTML templates are missing."""
        def side_effect(template_name, context):
            if template_name.endswith("_subject.txt"):
                return "Test Subject"
            else:
                raise TemplateDoesNotExist(template_name)

        mock_render_to_string.side_effect = side_effect

        with self.assertRaises(TemplateDoesNotExist):
            self.adapter.send_mail("missing_template", self.test_email, self.test_context)

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_whitespace_handling(self, mock_render_to_string, mock_send_email_task):
        """Test handling of whitespace in templates."""
        mock_render_to_string.side_effect = [
            "   Subject with spaces   \n\n",  # Subject with whitespace
            "   Text body with spaces   ",     # Text with whitespace
            "   <html><body>HTML with spaces</body></html>   ",  # HTML with whitespace
        ]

        self.adapter.send_mail("test_template", self.test_email, self.test_context)

        # Subject should have newlines removed but spaces preserved
        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="   Subject with spaces   ",
            contents="   <html><body>HTML with spaces</body></html>   ",
        )

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_unicode_templates(self, mock_render_to_string, mock_send_email_task):
        """Test handling of Unicode characters in templates."""
        mock_render_to_string.side_effect = [
            "Wëlcömë tö öür plätförm! 🎉\n",
            "Hëllö, plëäsë cönfïrm yöür ëmäïl äddröss.",
            "<html><body><h1>Wëlcömë! 🚀</h1></body></html>",
        ]

        self.adapter.send_mail("unicode_template", self.test_email, self.test_context)

        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="Wëlcömë tö öür plätförm! 🎉",
            contents="<html><body><h1>Wëlcömë! 🚀</h1></body></html>",
        )

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_empty_templates(self, mock_render_to_string, mock_send_email_task):
        """Test handling of empty template content."""
        mock_render_to_string.side_effect = [
            "",  # Empty subject
            "",  # Empty text
            "",  # Empty HTML
        ]

        self.adapter.send_mail("empty_template", self.test_email, self.test_context)

        # Should handle empty content gracefully
        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject="",
            contents="",  # Falls back to empty text when HTML is also empty
        )

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_long_content(self, mock_render_to_string, mock_send_email_task):
        """Test handling of long email content."""
        long_subject = "A" * 1000  # Very long subject
        long_text = "B" * 10000    # Very long text
        long_html = f"<html><body>{'C' * 10000}</body></html>"  # Very long HTML

        mock_render_to_string.side_effect = [
            long_subject + "\n",
            long_text,
            long_html,
        ]

        self.adapter.send_mail("long_template", self.test_email, self.test_context)

        mock_send_email_task.assert_called_once_with(
            to=self.test_email,
            subject=long_subject,  # Newline should be removed
            contents=long_html,
        )

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_special_characters_in_email(self, mock_render_to_string, mock_send_email_task):
        """Test sending mail to email addresses with special characters."""
        special_emails = [
            "test+tag@example.com",
            "test.with.dots@example.com",
            "test_with_underscores@example.com",
            "test-with-dashes@example.com",
        ]

        mock_render_to_string.side_effect = lambda *args: "Test content"

        for email in special_emails:
            with self.subTest(email=email):
                mock_send_email_task.reset_mock()
                
                self.adapter.send_mail("test_template", email, self.test_context)
                
                mock_send_email_task.assert_called_once()
                call_args = mock_send_email_task.call_args[1]
                self.assertEqual(call_args["to"], email)

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_context_isolation(self, mock_render_to_string, mock_send_email_task):
        """Test that context modifications don't affect subsequent calls."""
        original_context = {"key": "original_value"}
        
        # Track contexts passed to render_to_string without modifying them
        contexts_received = []
        
        def track_context_side_effect(template_name, context):
            # Store a copy of the context to check later
            contexts_received.append(copy.deepcopy(context))
            # Simulate template that would modify context (but we track before modification)
            context["key"] = "modified_value"
            return "Template content"

        mock_render_to_string.side_effect = track_context_side_effect

        # First call
        self.adapter.send_mail("signup_confirmation", self.test_email, original_context.copy())
        
        # Second call with fresh context
        fresh_context = {"key": "original_value"}
        self.adapter.send_mail("signup_confirmation", self.test_email, fresh_context)

        # Verify that all contexts received had the original value
        # This tests that our adapter properly isolates contexts
        for i, context in enumerate(contexts_received):
            self.assertEqual(context["key"], "original_value", 
                           f"Context {i} was modified before being passed to render_to_string")
        
        # Verify we received the expected number of calls (3 per send_mail call = 6 total)
        self.assertEqual(len(contexts_received), 6)


@pytest.mark.unit
class TestCustomAccountAdapterInheritance(TestCase):
    """Test custom account adapter inheritance and method overrides."""

    def setUp(self):
        """Set up test data."""
        self.adapter = CustomAccountAdapter()

    def test_adapter_inherits_from_default(self):
        """Test that adapter properly inherits from DefaultAccountAdapter."""
        from allauth.account.adapter import DefaultAccountAdapter
        self.assertIsInstance(self.adapter, DefaultAccountAdapter)

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_method_override(self, mock_render_to_string, mock_send_email_task):
        """Test that send_mail method is properly overridden."""
        mock_render_to_string.side_effect = [
            "Subject",
            "Text body",
            TemplateDoesNotExist("html template"),
        ]

        # Call the overridden method
        self.adapter.send_mail("test_template", "test@example.com", {})

        # Verify our custom implementation is called
        mock_send_email_task.assert_called_once()

    def test_adapter_other_methods_inherited(self):
        """Test that other adapter methods are properly inherited."""
        # These methods should exist from the parent class
        self.assertTrue(hasattr(self.adapter, 'get_login_redirect_url'))
        self.assertTrue(hasattr(self.adapter, 'get_logout_redirect_url'))
        self.assertTrue(hasattr(self.adapter, 'add_message'))

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_send_mail_signature_compatibility(self, mock_render_to_string, mock_send_email_task):
        """Test that send_mail signature is compatible with parent class."""
        mock_render_to_string.side_effect = [
            "Subject",  # subject template
            "Text body",  # text template
            "<html><body>HTML body</body></html>"  # html template
        ]

        # Should accept the same parameters as parent class
        try:
            self.adapter.send_mail(
                template_prefix="signup_confirmation",
                email="test@example.com",
                context={"key": "value"}
            )
        except TypeError:
            self.fail("send_mail signature is not compatible with parent class")

        mock_send_email_task.assert_called_once()


@pytest.mark.unit
class TestEmailAdapterIntegration(TestCase):
    """Test email adapter integration with Django allauth."""

    def setUp(self):
        """Set up test data."""
        self.adapter = CustomAccountAdapter()
        self.user = CustomUserFactory()

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_adapter_with_allauth_context(self, mock_render_to_string, mock_send_email_task):
        """Test adapter with typical allauth context data."""
        allauth_context = {
            "user": self.user,
            "activate_url": "http://example.com/activate/abc123",
            "key": "activation_key_123",
            "site": {"name": "Test Site", "domain": "example.com"},
            "request": Mock(),
        }

        mock_render_to_string.side_effect = [
            "Activate your account",
            f"Hello {self.user.username}, please activate your account.",
            f"<html><body>Hello {self.user.username}!</body></html>",
        ]

        self.adapter.send_mail(
            "account/email/email_confirmation",
            self.user.email,
            allauth_context
        )

        mock_send_email_task.assert_called_once_with(
            to=self.user.email,
            subject="Activate your account",
            contents=f"<html><body>Hello {self.user.username}!</body></html>",
        )

    @patch('apps.emails.adapters.send_email_task.delay')
    @patch('apps.emails.adapters.render_to_string')
    def test_adapter_template_not_found_fallback(self, mock_render_to_string, mock_send_email_task):
        """Test adapter fallback when templates are not found."""
        def side_effect(template_name, context):
            if "subject" in template_name:
                return "Default Subject"
            elif "message.txt" in template_name:
                return "Default text message"
            else:
                raise TemplateDoesNotExist(template_name)

        mock_render_to_string.side_effect = side_effect

        self.adapter.send_mail(
            "nonexistent/template",
            self.user.email,
            {"user": self.user}
        )

        # Should fall back to text content
        mock_send_email_task.assert_called_once_with(
            to=self.user.email,
            subject="Default Subject",
            contents="Default text message",
        )