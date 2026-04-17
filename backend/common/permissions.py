# =========================================================
# Common Permissions
# =========================================================

from django.contrib.auth.mixins import AccessMixin
from django.contrib import messages
from django.shortcuts import redirect


class AdminRequiredMixin(AccessMixin):
    """
    Verify that the current user is an Administrator (is_superuser or in 'Admins' group).
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name="Admins").exists()
        ):
            if request.htmx:
                from django.http import HttpResponse

                # HTMX cannot easily redirect with messages, so returning a 403 or error swap
                messages.error(request, "システム管理者のみ実行可能です。")
                return HttpResponse(status=204, headers={"HX-Trigger": "refreshList"})
            messages.error(request, "システム管理者のみ実行可能です。")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        return super().dispatch(request, *args, **kwargs)


class AccountantRequiredMixin(AccessMixin):
    """
    Verify that the current user is an Accountant or Admin (in 'Accountants' or 'Admins' group).
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_superuser or request.user.groups.filter(name__in=["Admins", "Accountants"]).exists()):
            if request.htmx:
                from django.http import HttpResponse

                messages.error(request, "会計担当者のみ実行可能です。")
                return HttpResponse(status=204, headers={"HX-Trigger": "refreshList"})
            messages.error(request, "会計担当者のみ実行可能です。")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        return super().dispatch(request, *args, **kwargs)
