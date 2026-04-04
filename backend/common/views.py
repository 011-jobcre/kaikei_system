from django.shortcuts import render


def messages_partial(request):
    """Return messages partial for HTMX to fetch after operations.

    Accepts optional `format` GET param: `inline` to return HTML for
    embedding into `#flash-messages`, `toast` to return toast markup.
    Default returns `toast` markup to show transient toasts.
    """
    fmt = request.GET.get("format", "toast")
    if fmt == "inline":
        return render(request, "includes/messages_inline.html")
    return render(request, "includes/messages_toast.html")
