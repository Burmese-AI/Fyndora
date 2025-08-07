import copy
import io

from allauth.account.adapter import DefaultAccountAdapter
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from .tasks import send_email_task


class CustomAccountAdapter(DefaultAccountAdapter):
    def _safe_copy_context(self, context):
        """
        Safely copy context dictionary, filtering out non-serializable objects
        like file handles, request objects, etc.
        """
        if not context:
            return {}

        safe_context = {}
        for key, value in context.items():
            try:
                # Try to deep copy the value
                safe_context[key] = copy.deepcopy(value)
            except (TypeError, AttributeError):
                # If deep copy fails, try shallow copy for basic types
                try:
                    if isinstance(value, (str, int, float, bool, list, dict, tuple)):
                        safe_context[key] = copy.copy(value)
                    elif hasattr(value, "__dict__") and not isinstance(
                        value, (io.IOBase, io.TextIOWrapper)
                    ):
                        # For objects with __dict__, try to copy their attributes
                        # but skip file-like objects
                        safe_context[key] = value
                    else:
                        # Skip non-serializable objects like file handles
                        continue
                except (TypeError, AttributeError):
                    # If all else fails, skip this key
                    continue

        return safe_context

    def send_mail(self, template_prefix, email, context):
        """
        Overrides the default send_mail to use our custom email service
        and correctly render HTML and text templates.
        """
        # Safely copy context to avoid pickle errors with file objects
        base_context = self._safe_copy_context(context)

        # Create completely independent copies for each template rendering
        # This ensures that modifications in one template don't affect others
        subject = render_to_string(
            f"{template_prefix}_subject.txt", self._safe_copy_context(base_context)
        )
        # Email subject *must not* contain newlines
        subject = "".join(subject.splitlines())

        try:
            text_body = render_to_string(
                f"{template_prefix}_message.txt", self._safe_copy_context(base_context)
            )
        except TemplateDoesNotExist:
            text_body = None

        try:
            html_body = render_to_string(
                f"{template_prefix}_message.html", self._safe_copy_context(base_context)
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
