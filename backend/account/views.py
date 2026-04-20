# =========================================================
# Authentication & Dashboard Views
# =========================================================

import calendar
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from journal.models import ShiwakeDenpyo, ShiwakeMeisai
from master.models import KanjoKamokuMaster, TorihikiSakiMaster


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
        now = timezone.localdate()
        month_start = now.replace(day=1)

        # KPI 1: Current Month Revenue & Expense
        # Revenue (SHUEKI): Sum(Credit) - Sum(Debit)
        revenue_agg = ShiwakeMeisai.objects.filter(
            denpyo__date__gte=month_start,
            denpyo__date__lte=now,
            kamoku__taisha_kubun="SHUEKI",
        ).aggregate(
            ka=Sum("kingaku", filter=Q(kari_kashi="KA")),
            sh=Sum("kingaku", filter=Q(kari_kashi="SHI")),
        )
        monthly_revenue = (revenue_agg["sh"] or Decimal("0")) - (revenue_agg["ka"] or Decimal("0"))

        # Expense (HIYO): Sum(Debit) - Sum(Credit)
        expense_agg = ShiwakeMeisai.objects.filter(
            denpyo__date__gte=month_start,
            denpyo__date__lte=now,
            kamoku__taisha_kubun="HIYO",
        ).aggregate(
            ka=Sum("kingaku", filter=Q(kari_kashi="KA")),
            sh=Sum("kingaku", filter=Q(kari_kashi="SHI")),
        )
        monthly_expense = (expense_agg["ka"] or Decimal("0")) - (expense_agg["sh"] or Decimal("0"))
        net_income = monthly_revenue - monthly_expense

        # KPI 2: Current Cash & Deposit Balance (Total active)
        # Summing accounts with "現金" or "預金" in name
        cash_kamoku_ids = KanjoKamokuMaster.objects.filter(
            Q(name__contains="現金") | Q(name__contains="預金"), level=4, is_active=True
        ).values_list("id", flat=True)

        cash_agg = ShiwakeMeisai.objects.filter(kamoku_id__in=cash_kamoku_ids).aggregate(
            ka=Sum("kingaku", filter=Q(kari_kashi="KA")),
            sh=Sum("kingaku", filter=Q(kari_kashi="SHI")),
        )
        cash_balance = (cash_agg["ka"] or Decimal("0")) - (cash_agg["sh"] or Decimal("0"))

        # Chart Data: Last 6 Months Trends
        chart_labels = []
        revenue_trend = []
        expense_trend = []

        for i in range(5, -1, -1):
            target_month = now - relativedelta(months=i)
            t_start = target_month.replace(day=1)
            t_end = target_month.replace(day=calendar.monthrange(target_month.year, target_month.month)[1])

            # Revenue for target month
            r_agg = ShiwakeMeisai.objects.filter(
                denpyo__date__gte=t_start,
                denpyo__date__lte=t_end,
                kamoku__taisha_kubun="SHUEKI",
            ).aggregate(
                ka=Sum("kingaku", filter=Q(kari_kashi="KA")),
                sh=Sum("kingaku", filter=Q(kari_kashi="SHI")),
            )
            revenue_trend.append(float((r_agg["sh"] or 0) - (r_agg["ka"] or 0)))

            # Expense for target month
            e_agg = ShiwakeMeisai.objects.filter(
                denpyo__date__gte=t_start,
                denpyo__date__lte=t_end,
                kamoku__taisha_kubun="HIYO",
            ).aggregate(
                ka=Sum("kingaku", filter=Q(kari_kashi="KA")),
                sh=Sum("kingaku", filter=Q(kari_kashi="SHI")),
            )
            expense_trend.append(float((e_agg["ka"] or 0) - (e_agg["sh"] or 0)))
            chart_labels.append(target_month.strftime("%Y/%m"))

        # Activity & Counts
        recent_vouchers = ShiwakeDenpyo.objects.all().order_by("-id")[:5]
        unlocked_in_month = ShiwakeDenpyo.objects.filter(date__gte=month_start, date__lte=now, is_locked=False).count()

        kamoku_count = KanjoKamokuMaster.objects.filter(is_active=True).count()
        torihiki_count = TorihikiSakiMaster.objects.filter(is_active=True).count()

        return render(
            request,
            self.template_name,
            {
                "monthly_revenue": monthly_revenue,
                "monthly_expense": monthly_expense,
                "net_income": net_income,
                "cash_balance": cash_balance,
                "chart_labels": chart_labels,
                "revenue_trend": revenue_trend,
                "expense_trend": expense_trend,
                "recent_vouchers": recent_vouchers,
                "unlocked_in_month": unlocked_in_month,
                "kamoku_count": kamoku_count,
                "torihiki_count": torihiki_count,
                "current_month": now.strftime("%Y年%m月"),
            },
        )
