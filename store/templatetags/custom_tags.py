from django import template

register = template.Library()

@register.filter
def has_organizer(user):
    """Check if the user has an Organizer object linked."""
    return hasattr(user, "organizer")