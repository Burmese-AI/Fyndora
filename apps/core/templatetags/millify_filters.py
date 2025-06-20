from django import template
from millify import millify

register = template.Library()


@register.filter
def millify_number(value):
    try:
        return millify(value)
    except:
        return value
