from allauth.account.adapter import DefaultAccountAdapter
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
import copy

from .tasks import send_email_task


class CustomAccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        """
        Overrides the default send_mail to use our custom email service
        and correctly render HTML and text templates.
        """
        # Ensure we never modify the original context by creating a base copy first
        base_context = copy.deepcopy(context) if context else {}

        # Create completely independent copies for each template rendering
        # This ensures that modifications in one template don't affect others
        subject = render_to_string(
            f"{template_prefix}_subject.txt", copy.deepcopy(base_context)
        )
        # Email subject *must not* contain newlines
        subject = "".join(subject.splitlines())

        try:
            text_body = render_to_string(
                f"{template_prefix}_message.txt", copy.deepcopy(base_context)
            )
        except TemplateDoesNotExist:
            text_body = None

        try:
            html_body = render_to_string(
                f"{template_prefix}_message.html", copy.deepcopy(base_context)
            )
        except TemplateDoesNotExist:
            html_body = None

        # Use HTML if available and not empty, otherwise text, otherwise raise error for missing templates
        if html_body is not None and isinstance(html_body, str) and html_body.strip():
            contents = html_body
        elif text_body is not None:
            contents = text_body
        else:
            # If both templates are missing (not just empty), raise the exception
            raise TemplateDoesNotExist(
                f"Neither {template_prefix}_message.txt nor {template_prefix}_message.html found"
            )

        send_email_task.delay(to=email, subject=subject, contents=contents)
