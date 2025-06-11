from django import template
from apps.invitations.utils import get_invitation_url

register = template.Library()

# Custom template tag to generate invitation URL
# Usage: {% invitation_url invitation %}
@register.simple_tag(takes_context=True)
def invitation_url(context, invitation, domain_override=None):
    request = context.get('request')
    return get_invitation_url(request=request, invitation=invitation, domain_override=domain_override)