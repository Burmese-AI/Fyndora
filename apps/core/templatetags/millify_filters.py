from django import template
from millify import millify

register = template.Library()


@register.filter
def millify_number(value, precision=1):
    try:
        return millify(float(value), precision=int(precision))
    except Exception as e:
        print(f"Error in millify_number: {e}")
