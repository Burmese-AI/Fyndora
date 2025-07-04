from allauth.account.adapter import DefaultAccountAdapter
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from .tasks import send_email_task


class CustomAccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        """
        Overrides the default send_mail to use our custom email service
        and correctly render HTML and text templates.
        """
        subject = render_to_string(f'{template_prefix}_subject.txt', context)
        # Email subject *must not* contain newlines
        subject = "".join(subject.splitlines())

        # Render text and HTML versions
        text_body = render_to_string(f'{template_prefix}_message.txt', context)

        try:
            html_body = render_to_string(f'{template_prefix}_message.html', context)
        except TemplateDoesNotExist:
            html_body = None

        # Our email service will send the HTML version if it exists,
        send_email_task.delay(to=email, subject=subject, contents=[text_body, html_body])
