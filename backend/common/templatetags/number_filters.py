from django import template

register = template.Library()


@register.filter
def format_number(value):
    """
    Format a number with dots as thousand separators, no decimals.
    """
    if value is None:
        return ""
    try:
        # Convert to int and format with dots as thousand separators
        num = int(value)
        # Use string formatting to add dots
        s = f"{num:,}".replace(",", ".")
        return s
    except (ValueError, TypeError):
        return str(value)
