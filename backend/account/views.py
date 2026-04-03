from decimal import Decimal

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import redirect, render
from django.views import View

from journal.models import ShiwakeDenpyo
from master.models import BumonMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("account:dashboard")
        form = AuthenticationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(request.GET.get("next", "account:dashboard"))
        return render(request, self.template_name, {"form": form})


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        return redirect("account:login")


class DashboardView(LoginRequiredMixin, View):
    template_name = "accounts/dashboard.html"

    def get(self, request):
        # Current month statistics
        from django.utils import timezone

        now = timezone.localdate()
        month_start = now.replace(day=1)

        denpyo_count = ShiwakeDenpyo.objects.filter(
            date__gte=month_start, date__lte=now
        ).count()
        locked_count = ShiwakeDenpyo.objects.filter(is_locked=True).count()
        kamoku_count = KanjoKamokuMaster.objects.filter(is_active=True).count()
        torihiki_count = TorihikiSakiMaster.objects.filter(is_active=True).count()

        return render(
            request,
            self.template_name,
            {
                "denpyo_count": denpyo_count,
                "locked_count": locked_count,
                "kamoku_count": kamoku_count,
                "torihiki_count": torihiki_count,
                "current_month": now.strftime("%Y年%m月"),
            },
        )


class TestView(LoginRequiredMixin, View):
    template_name = "accounts/test.html"

    def get(self, request):
        # Test view
        return render(request, self.template_name)
