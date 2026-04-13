# =========================================================
# Common Utility Views
# =========================================================

from django.shortcuts import render


def messages_partial(request):
    """Return combined inline and toast messages for HTMX to fetch after operations."""
    return render(request, "includes/messages_inline.html")
