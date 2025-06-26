# templatetags/entry_tags.py
from django import template

register = template.Library()


@register.filter
def entry_status_color(status):
    return {
        "approved": "badge-success",
        "pending_review": "badge-warning",
        "flagged": "badge-secondary",
        "rejected": "badge-error",
    }.get(status, "badge-neutral")


@register.filter
def entry_type_color(entry_type):
    return {
        "income": "badge-info",
        "disbursement": "badge-error",
        "remittance": "badge-warning",
        "workspace_exp": "badge-primary",
        "org_exp": "badge-accent",
    }.get(entry_type, "badge-neutral")
