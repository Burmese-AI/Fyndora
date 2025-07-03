from allauth.account.adapter import DefaultAccountAdapter

from .services import send_email


class CustomAccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        subject = self.render_mail(f"{template_prefix}_subject", email, context).strip()
        body = self.render_mail(f"{template_prefix}_message", email, context)
        send_email(to=email, subject=subject, contents=body)
