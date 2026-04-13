from django.utils import timezone
import json
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from common.permissions import AccountantRequiredMixin, AdminRequiredMixin

from .forms import MeisaiFormSet, ShiwakeDenpyoForm, ShiwakeMeisaiForm
from .models import ShiwakeDenpyo, ShiwakeMeisai


from master.views import HtmxListMixin


# =========================================================
# Mixins: shared HTMX behaviour for journal views
# =========================================================


class HtmxModalMixin:
    """
    Mixin for Create/Update views that handle formsets and are triggered by HTMX from a modal dialog.

    On success  → returns an empty 200 response with HX-Trigger: refreshList,
                  which signals the list partial to reload itself via HTMX.
    On failure  → re-renders only the modal template with inline validation errors,
                  so the user can correct them without losing the modal.
    """

    def get_formset(self):
        """Override to return the formset instance."""
        return None

    def form_valid(self, form):
        formset = self.get_formset()
        if formset and not formset.is_valid():
            return self.form_invalid(form)

        response = super().form_valid(form)
        if self.request.htmx:
            # Empty body + HX-Trigger tells the list partial to refresh itself
            return HttpResponse(
                "",
                status=200,
                headers={"HX-Trigger": "refreshList"},
            )
        return response

    def form_invalid(self, form):
        if self.request.htmx:
            # Re-render the modal template with form errors visible
            return render(
                self.request,
                self.template_name,
                self.get_context_data(form=form),
            )
        return super().form_invalid(form)


# =========================================================
# Journal Ledger Views (List)
# =========================================================
class DenpyoListView(LoginRequiredMixin, HtmxListMixin, ListView):
    model = ShiwakeDenpyo
    template_name = "journal/denpyo_list.html"
    partial_template_name = "journal/partials/denpyo_table.html"
    context_object_name = "denpyo_list"
    paginate_by = 30

    def get_queryset(self):
        qs = ShiwakeDenpyo.objects.select_related("created_by").prefetch_related("meisai__kamoku")
        q = self.request.GET.get("q", "")
        date_from = self.request.GET.get("date_from", "")
        date_to = self.request.GET.get("date_to", "")
        if q:
            qs = qs.filter(denpyo_no__icontains=q) | qs.filter(memo__icontains=q)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["date_from"] = self.request.GET.get("date_from", "")
        ctx["date_to"] = self.request.GET.get("date_to", "")
        return ctx


# =========================================================
# Voucher Management (Create)
# =========================================================
class DenpyoCreateView(AccountantRequiredMixin, HtmxModalMixin, CreateView):
    model = ShiwakeDenpyo
    form_class = ShiwakeDenpyoForm
    template_name = "journal/denpyo_form.html"
    success_url = reverse_lazy("journal:denpyo-list")

    def get_formset(self):
        if self.request.method == "POST":
            return MeisaiFormSet(self.request.POST)
        return MeisaiFormSet()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = self.get_formset()
        ctx["title"] = "振替伝票 新規作成"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        formset = self.get_formset()
        if not formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.save()
            formset.instance = self.object
            formset.save()

        messages.success(self.request, f"伝票「{self.object.denpyo_no}」を新規登録しました。")
        return super().form_valid(form)


# =========================================================
# Voucher Management (Update)
# =========================================================
class DenpyoUpdateView(AccountantRequiredMixin, HtmxModalMixin, UpdateView):
    model = ShiwakeDenpyo
    form_class = ShiwakeDenpyoForm
    template_name = "journal/denpyo_form.html"
    success_url = reverse_lazy("journal:denpyo-list")

    def get_formset(self):
        if self.request.method == "POST":
            return MeisaiFormSet(self.request.POST, instance=self.object)
        return MeisaiFormSet(instance=self.object)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = self.get_formset()
        ctx["title"] = f"振替伝票 編集: {self.object.denpyo_no}"
        ctx["is_new"] = False
        ctx["denpyo"] = self.object
        return ctx

    def form_valid(self, form):
        formset = self.get_formset()
        if not formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

        messages.success(self.request, f"伝票「{self.object.denpyo_no}」を更新しました。")
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_locked:
            messages.error(request, "この伝票はロックされており編集できません。")
            return redirect(self.success_url)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_locked:
            messages.error(request, "ロックされた伝票は編集できません。")
            if request.htmx:
                return HttpResponse(status=409)
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)


# =========================================================
# Voucher Management (Delete)
# =========================================================
class DenpyoDeleteView(AccountantRequiredMixin, DeleteView):
    model = ShiwakeDenpyo
    template_name = "journal/partials/delete_confirm.html"
    success_url = reverse_lazy("journal:denpyo-list")

    def form_valid(self, form):
        denpyo = self.get_object()
        if denpyo.is_locked:
            messages.error(self.request, "ロックされた伝票は削除できません。")
            if self.request.htmx:
                return render(self.request, self.template_name, self.get_context_data())
            return redirect(self.success_url)
        no = denpyo.denpyo_no
        denpyo.delete()
        messages.success(self.request, f"伝票「{no}」を削除しました。")
        if self.request.htmx:
            return HttpResponse(
                "",
                status=200,
                headers={"HX-Redirect": str(self.success_url)},
            )
        return redirect(self.success_url)


# =========================================================
# HTMX: Voucher Management Helpers
# =========================================================
def add_meisai_row(request):
    """Called from HTMX — return an empty detail row HTML."""
    form_index = int(request.GET.get("form_index", 0))
    form = ShiwakeMeisaiForm(prefix=f"meisai-{form_index}")
    return render(
        request,
        "journal/partials/meisai_row.html",
        {
            "form": form,
            "form_index": form_index,
        },
    )


def balance_check(request):
    """Called from HTMX — return current debit/credit total difference for inputs."""
    try:
        kari = float(request.GET.get("kari", 0) or 0)
        kashi = float(request.GET.get("kashi", 0) or 0)
    except (ValueError, TypeError):
        kari = kashi = 0.0
    diff = kari - kashi
    return render(
        request,
        "journal/partials/balance_bar.html",
        {
            "kari_total": kari,
            "kashi_total": kashi,
            "diff": diff,
            "balanced": diff == 0,
        },
    )


# =========================================================
# Monthly Period Closing Views
# =========================================================
class GetsujiShimeListView(LoginRequiredMixin, View):
    """Monthly Closing List: Displays the status of monthly period locks"""

    template_name = "journal/getsuji_shime.html"

    def get(self, request):
        # 月ごとに伝票数・金額・締め状況を集計
        months_qs = (
            ShiwakeDenpyo.objects.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(
                denpyo_count=Count("id"),
                locked_count=Count("id", filter=models.Q(is_locked=True)),
            )
            .order_by("-month")
        )

        months = []
        for m in months_qs:
            month_dt = m["month"]
            total = m["denpyo_count"]
            total_locked = m["locked_count"]
            # Check if all vouchers in the month are locked
            is_fully_locked = total > 0 and total_locked == total
            months.append(
                {
                    "month": month_dt,
                    "month_str": month_dt.strftime("%Y-%m"),
                    "label": month_dt.strftime("%Y/%m"),
                    "denpyo_count": total,
                    "locked_count": total_locked,
                    "is_fully_locked": is_fully_locked,
                }
            )
        return render(request, self.template_name, {"months": months})


class NenjiKessanView(AdminRequiredMixin, View):
    """Year-End Closing and Carry-forward View"""

    template_name = "journal/nenji_kessan.html"

    def get(self, request):
        return render(request, self.template_name, {"fiscal_year_list": self.get_fiscal_year_list()})

    def post(self, request):
        year_str = request.POST.get("fiscal_year")
        if not year_str:
            messages.error(request, "対象年度を選択してください。")
            return redirect("journal:nenji-kessan")

        try:
            year = int(year_str)
            from datetime import date

            date_from = date(year, 4, 1)
            date_to = date(year + 1, 3, 31)
        except ValueError:
            messages.error(request, "対象年度の形式が正しくありません。")
            return redirect("journal:nenji-kessan")

        # Get P/L Accounts
        try:
            from master.models import KanjoKamokuMaster
        except ImportError:
            pass

        pl_kamokus = KanjoKamokuMaster.objects.filter(level=4, taisha_kubun__in=["SHUEKI", "HIYO"]).order_by("code")

        # Get Retained Earnings account
        retained_earnings = KanjoKamokuMaster.objects.filter(level=4, name="繰越利益剰余金").first()

        if not retained_earnings:
            messages.error(request, "繰越利益剰余金勘定が見つかりません。")
            return redirect("journal:nenji-kessan")

        with transaction.atomic():
            # Create a single closing denpyo
            kessan_denpyo = ShiwakeDenpyo.objects.create(
                date=date_to, memo=f"Fiscal Year {year} Closing Entry", created_by=request.user, is_locked=False
            )

            for kamoku in pl_kamokus:
                # Calculate balance
                qs = ShiwakeMeisai.objects.filter(
                    kamoku=kamoku, denpyo__date__gte=date_from, denpyo__date__lte=date_to
                ).exclude(
                    denpyo=kessan_denpyo
                )  # Exclude in case we run it multiple times by mistake, wait just normally exclude current

                kari_sum = qs.filter(kari_kashi="KA").aggregate(total=Sum("kingaku"))["total"] or Decimal("0")
                kashi_sum = qs.filter(kari_kashi="SHI").aggregate(total=Sum("kingaku"))["total"] or Decimal("0")

                balance = Decimal("0")
                if kamoku.is_kari_zandaka:
                    balance = kari_sum - kashi_sum
                else:
                    balance = kashi_sum - kari_sum

                if balance == Decimal("0"):
                    continue

                # Creating offsetting entries to clear the balance
                # Profit/Loss offset goes to RE
                if kamoku.is_kari_zandaka:  # e.g. Expenses
                    if balance > 0:
                        # Clear Expense -> Kashi
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="SHI",
                            kamoku=kamoku,
                            kingaku=balance,
                            tekyou="Closing Entry",
                        )
                        # Debit Retained Earnings
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="KA",
                            kamoku=retained_earnings,
                            kingaku=balance,
                            tekyou=f"Closing Entry ({kamoku.name})",
                        )
                    elif balance < 0:
                        # Negative Expense -> Debit to clear
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="KA",
                            kamoku=kamoku,
                            kingaku=abs(balance),
                            tekyou="Closing Entry",
                        )
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="SHI",
                            kamoku=retained_earnings,
                            kingaku=abs(balance),
                            tekyou=f"Closing Entry ({kamoku.name})",
                        )
                else:  # e.g. Revenue
                    if balance > 0:
                        # Clear Revenue -> Kari
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="KA",
                            kamoku=kamoku,
                            kingaku=balance,
                            tekyou="Closing Entry",
                        )
                        # Credit Retained Earnings
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="SHI",
                            kamoku=retained_earnings,
                            kingaku=balance,
                            tekyou=f"Closing Entry ({kamoku.name})",
                        )
                    elif balance < 0:
                        # Negative Revenue -> Kashi to clear
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="SHI",
                            kamoku=kamoku,
                            kingaku=abs(balance),
                            tekyou="Closing Entry",
                        )
                        ShiwakeMeisai.objects.create(
                            denpyo=kessan_denpyo,
                            kari_kashi="KA",
                            kamoku=retained_earnings,
                            kingaku=abs(balance),
                            tekyou=f"Closing Entry ({kamoku.name})",
                        )

                # If the denpyo has no meisai, delete it
                messages.info(request, f"対象年度の損益データがありません。")
            else:
                messages.success(request, f"対象年度の決算整理仕訳伝票（{kessan_denpyo.denpyo_no}）を作成しました。")

        return redirect("journal:nenji-kessan")

    def get_fiscal_year_list(self):
        """Return list of fiscal years"""
        # Display 3 years starting from the year after the last closed year
        year = timezone.now().year
        return range(2025, year + 2)


class GetsujiShimeToggleView(AdminRequiredMixin, View):
    """Monthly Lock/Unlock: Lock or unlock all vouchers in a specific month (Admin only)"""

    def post(self, request):
        month_str = request.POST.get("month_str", "")  # e.g. "2026-01"
        action = request.POST.get("action", "lock")  # "lock" or "unlock"

        if not month_str:
            messages.error(request, "対象月が指定されていません。")
            return redirect("journal:getsuji-shime")

        try:
            from datetime import date

            year, month = map(int, month_str.split("-"))
            # Compute first and last day of the month
            import calendar

            last_day = calendar.monthrange(year, month)[1]
            date_from = date(year, month, 1)
            date_to = date(year, month, last_day)
        except (ValueError, TypeError):
            messages.error(request, "対象月の形式が正しくありません。")
            return redirect("journal:getsuji-shime")

        lock_value = action == "lock"
        updated = ShiwakeDenpyo.objects.filter(date__gte=date_from, date__lte=date_to).update(is_locked=lock_value)

        month_label = f"{year}/{month:02d}"
        if lock_value:
            messages.success(request, f"{month_label}の伝票を{updated}件クローズしました。")
        else:
            messages.success(request, f"{month_label}の伝票を{updated}件アンクローズしました。")

        return redirect("journal:getsuji-shime")
