# =========================================================
# Journal Views
# =========================================================

import calendar
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models, transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DeleteView, ListView

from common.permissions import AccountantRequiredMixin, AdminRequiredMixin
from master.models import KanjoKamokuMaster
from master.views import HtmxListMixin

from .forms import MeisaiFormSet, FurikaeHeaderForm, FurikaeMeisaiForm, ShiwakeMeisaiForm
from .models import ShiwakeDenpyo, ShiwakeMeisai


# =========================================================
# Shiwake Ichiran — Journal List View (仕訳一覧)
# =========================================================


class ShiwakeListView(LoginRequiredMixin, HtmxListMixin, ListView):
    """仕訳一覧: Unified list of all vouchers (both Shiwake and Furikae types).

    Filter by date range, keyword, and voucher type.
    """

    model = ShiwakeDenpyo
    template_name = "journal/shiwake_list.html"
    partial_template_name = "journal/partials/shiwake_list_table.html"
    context_object_name = "denpyo_list"
    title = "仕訳日記帳"
    paginate_by = 30

    def get_queryset(self):
        qs = (
            ShiwakeDenpyo.objects.select_related("created_by")
            .prefetch_related("meisai__kamoku", "meisai__hojo", "meisai__torihikisaki")
            .annotate(
                meisai_count=Count("meisai", distinct=True),
                kari_total=Sum("meisai__kingaku", filter=Q(meisai__kari_kashi="KA")),
                kashi_total=Sum("meisai__kingaku", filter=Q(meisai__kari_kashi="SHI")),
            )
        )
        q = self.request.GET.get("q", "")
        date_from = self.request.GET.get("date_from", "")
        date_to = self.request.GET.get("date_to", "")
        denpyo_type = self.request.GET.get("denpyo_type", "")
        if q:
            qs = qs.filter(
                Q(denpyo_no__icontains=q)
                | Q(memo__icontains=q)
                | Q(meisai__tekyou__icontains=q)
                | Q(meisai__kamoku__name__icontains=q)
                | Q(meisai__torihikisaki__name__icontains=q)
            )
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if denpyo_type in ("SHIWAKE", "FURIKAE"):
            qs = qs.filter(denpyo_type=denpyo_type)
        return qs.distinct().order_by("-date", "-denpyo_no")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.title
        ctx["q"] = self.request.GET.get("q", "")
        ctx["date_from"] = self.request.GET.get("date_from", "")
        ctx["date_to"] = self.request.GET.get("date_to", "")
        ctx["denpyo_type"] = self.request.GET.get("denpyo_type", "")
        return ctx


# =========================================================
# Shiwake Nikki — Spreadsheet Grid Entry (仕訳日記帳)
# =========================================================


class ShiwakeNikkiCreateView(AccountantRequiredMixin, View):
    """仕訳日記帳: Create a general single-line for direct (1:1) journal entry.

    Allows entering multiple rows in a table format. Each row is saved as a
    standalone balanced voucher (S- prefix).
    """

    template_name = "journal/shiwake_form.html"
    success_url = reverse_lazy("journal:shiwake-list")

    def get(self, request):
        # We'll provide 5 empty rows initially
        today = timezone.localdate()
        rows = [ShiwakeMeisaiForm(prefix=f"row-{i}", initial={"date": today}) for i in range(5)]

        # Also get recent entries for display below the input grid
        recent_shiwake = ShiwakeDenpyo.objects.filter(denpyo_type="SHIWAKE").order_by("-id")[:10]

        return render(
            request,
            self.template_name,
            {
                "title": "仕訳日記帳 新規作成",
                "rows": rows,
                "recent_shiwake": recent_shiwake,
                "is_new": True,
            },
        )

    def post(self, request):
        # Determine prefix from GET/POST parameters or detect from field names
        prefix = request.GET.get("row_index")
        if prefix:
            prefix = f"row-{prefix}"

        if not prefix:
            prefix = request.POST.get("_row_prefix")

        if not prefix:
            for key in request.POST.keys():
                if key.startswith("row-") and "-" in key[4:]:
                    prefix = key.split("-")[0] + "-" + key.split("-")[1]
                    break

        form = ShiwakeMeisaiForm(request.POST, prefix=prefix)

        if form.is_valid():
            with transaction.atomic():
                d = form.cleaned_data
                denpyo = ShiwakeDenpyo.objects.create(
                    date=d["date"],
                    denpyo_type="SHIWAKE",
                    memo=d["tekiyou"] or "",
                    created_by=request.user,
                )
                # Debit Side
                ShiwakeMeisai.objects.create(
                    denpyo=denpyo,
                    row_no=0,
                    kari_kashi="KA",
                    kamoku=d["kari_kamoku"],
                    hojo=d.get("kari_hojo"),
                    kingaku=d["kari_kingaku"],
                    zei_kubun=d.get("kari_zei"),
                    tekyou=d["tekiyou"],
                    bumon=d.get("bumon"),
                    torihikisaki=d.get("torihikisaki"),
                )
                # Credit Side
                ShiwakeMeisai.objects.create(
                    denpyo=denpyo,
                    row_no=1,
                    kari_kashi="SHI",
                    kamoku=d["kashi_kamoku"],
                    hojo=d.get("kashi_hojo"),
                    kingaku=d["kashi_kingaku"],
                    zei_kubun=d.get("kashi_zei"),
                    tekyou=d["tekiyou"],
                    bumon=d.get("bumon"),
                    torihikisaki=d.get("torihikisaki"),
                )

            if request.htmx:
                new_form = ShiwakeMeisaiForm(prefix=prefix, initial={"date": timezone.localdate()})
                row_index = prefix.split("-")[1] if prefix and "-" in prefix else 0
                response = render(
                    request,
                    "journal/partials/shiwake_form_meisai.html",
                    {
                        "form": new_form,
                        "row_index": row_index,
                    },
                )
                response["HX-Trigger"] = "refreshRecentEntries"
                return response

            messages.success(request, f"伝票 {denpyo.denpyo_no} を登録しました")
            return redirect(self.success_url)

        if request.htmx:
            # Return form with errors
            row_index = prefix.split("-")[1] if prefix and "-" in prefix else 0
            return render(request, "journal/partials/shiwake_form_meisai.html", {"form": form, "row_index": row_index})

        return self.get(request)


# =========================================================
# Furikae Denpyo — Professional Multi-line Entry (振替伝票)
# =========================================================


class FurikaeDenpyoCreateView(AccountantRequiredMixin, View):
    """振替伝票: Create a general multi-line (N:N) journal entry.

    Uses MeisaiFormSet allowing multiple debit and credit rows.
    Automatically sets denpyo_type=FURIKAE and assigns F- voucher number.
    """

    template_name = "journal/furikae_form.html"
    success_url = reverse_lazy("journal:shiwake-list")

    def _get_formset(self, data=None):
        prefix = "meisai"
        if data:
            return MeisaiFormSet(data, prefix=prefix)
        return MeisaiFormSet(prefix=prefix)

    def get(self, request):
        form = FurikaeHeaderForm()
        formset = self._get_formset()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "title": "振替伝票 新規作成",
                "is_new": True,
            },
        )

    def post(self, request):
        form = FurikaeHeaderForm(request.POST)
        formset = self._get_formset(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                denpyo = form.save(commit=False)
                denpyo.denpyo_type = "FURIKAE"
                denpyo.created_by = request.user
                denpyo.save()
                formset.instance = denpyo
                instances = formset.save(commit=False)
                for i, obj in enumerate(instances):
                    obj.row_no = i
                    obj.save()
                for obj in formset.deleted_objects:
                    obj.delete()
            messages.success(request, f"振替伝票「{denpyo.denpyo_no}」を新規登録しました。")
            return redirect(self.success_url)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "is_new": True,
            },
        )


class FurikaeDenpyoUpdateView(AccountantRequiredMixin, View):
    """振替伝票: Edit an existing multi-line journal entry."""

    template_name = "journal/furikae_form.html"
    success_url = reverse_lazy("journal:shiwake-list")

    def _get_object(self, pk):
        return ShiwakeDenpyo.objects.get(pk=pk)

    def _get_formset(self, denpyo, data=None):
        prefix = "meisai"
        if data:
            return MeisaiFormSet(data, instance=denpyo, prefix=prefix)
        return MeisaiFormSet(instance=denpyo, prefix=prefix)

    def get(self, request, pk):
        denpyo = self._get_object(pk)
        if denpyo.is_locked:
            messages.error(request, "この伝票はロックされており編集できません。")
            return redirect(self.success_url)
        form = FurikaeHeaderForm(instance=denpyo)
        formset = self._get_formset(denpyo)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "denpyo": denpyo,
                "title": f"{denpyo.get_denpyo_type_display()}伝票 編集: {denpyo.denpyo_no}",
                "is_new": False,
            },
        )

    def post(self, request, pk):
        denpyo = self._get_object(pk)
        if denpyo.is_locked:
            messages.error(request, "ロックされた伝票は編集できません。")
            return redirect(self.success_url)
        form = FurikaeHeaderForm(request.POST, instance=denpyo)
        formset = self._get_formset(denpyo, request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                instances = formset.save(commit=False)
                for i, obj in enumerate(instances):
                    obj.row_no = i
                    obj.save()
                for obj in formset.deleted_objects:
                    obj.delete()
            messages.success(request, f"振替伝票「{denpyo.denpyo_no}」を更新しました。")
            return redirect(self.success_url)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "denpyo": denpyo,
                "is_new": False,
            },
        )


# =========================================================
# Voucher Delete (shared for both types)
# =========================================================


class DenpyoDeleteView(AccountantRequiredMixin, DeleteView):
    """Delete a voucher (either Shiwake or Furikae). Locked entries cannot be deleted."""

    model = ShiwakeDenpyo
    template_name = "journal/partials/delete_confirm.html"
    success_url = reverse_lazy("journal:shiwake-list")

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
            return HttpResponse("", status=200, headers={"HX-Redirect": str(self.success_url)})
        return redirect(self.success_url)


# =========================================================
# HTMX Helpers
# =========================================================


def add_form_row(request):
    """HTMX endpoint — add empty row for shiwake or furikae forms.

    Args:
        form_type: 'shiwake' or 'furikae'
        index: row index for prefix
    """

    form_type = request.GET.get("form_type", "shiwake")
    index = int(request.GET.get("index", 0))

    if form_type == "furikae":
        form = FurikaeMeisaiForm(prefix=f"meisai-{index}")
        template = "journal/partials/furikae_form_meisai.html"
        context = {"form": form, "form_index": index}
    else:  # shiwake
        form = ShiwakeMeisaiForm(prefix=f"row-{index}", initial={"date": timezone.localdate()})
        template = "journal/partials/shiwake_form_meisai.html"
        context = {"form": form, "row_index": index}

    return render(request, template, context)


def recent_shiwake_entries(request):
    """HTMX endpoint — refresh the recent shiwake entries panel."""
    recent_shiwake = (
        ShiwakeDenpyo.objects.filter(denpyo_type="SHIWAKE").prefetch_related("meisai__kamoku").order_by("-id")[:10]
    )
    return render(
        request,
        "journal/partials/shiwake_form_recent.html",
        {
            "recent_shiwake": recent_shiwake,
        },
    )


def balance_check(request):
    """HTMX endpoint — return current debit/credit balance indicator."""
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


class GetsujiShimeToggleView(AdminRequiredMixin, View):
    """Monthly Lock/Unlock: Lock or unlock all vouchers in a specific month (Admin only)"""

    def post(self, request):
        month_str = request.POST.get("month_str", "")
        action = request.POST.get("action", "lock")

        if not month_str:
            messages.error(request, "対象月が指定されていません。")
            return redirect("journal:getsuji-shime")

        try:
            year, month = map(int, month_str.split("-"))
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


# =========================================================
# Year-End Closing View
# =========================================================


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
            date_from = date(year, 4, 1)
            date_to = date(year + 1, 3, 31)
        except ValueError:
            messages.error(request, "対象年度の形式が正しくありません。")
            return redirect("journal:nenji-kessan")

        pl_kamokus = KanjoKamokuMaster.objects.filter(level=4, taisha_kubun__in=["SHUEKI", "HIYO"]).order_by("code")
        retained_earnings = KanjoKamokuMaster.objects.filter(level=4, name="繰越利益剰余金").first()

        if not retained_earnings:
            messages.error(request, "繰越利益剰余金勘定が見つかりません。")
            return redirect("journal:nenji-kessan")

        with transaction.atomic():
            kessan_denpyo = ShiwakeDenpyo.objects.create(
                date=date_to,
                denpyo_type="SHIWAKE",
                memo=f"Fiscal Year {year} Closing Entry",
                created_by=request.user,
                is_locked=False,
            )
            row = 0
            for kamoku in pl_kamokus:
                qs = ShiwakeMeisai.objects.filter(
                    kamoku=kamoku,
                    denpyo__date__gte=date_from,
                    denpyo__date__lte=date_to,
                ).exclude(denpyo=kessan_denpyo)
                kari_sum = qs.filter(kari_kashi="KA").aggregate(total=Sum("kingaku"))["total"] or Decimal("0")
                kashi_sum = qs.filter(kari_kashi="SHI").aggregate(total=Sum("kingaku"))["total"] or Decimal("0")
                balance = (kari_sum - kashi_sum) if kamoku.is_kari_zandaka else (kashi_sum - kari_sum)
                if balance == Decimal("0"):
                    continue

                if kamoku.is_kari_zandaka:  # Expenses
                    kk1, kk2 = ("SHI", "KA") if balance > 0 else ("KA", "SHI")
                else:  # Revenue
                    kk1, kk2 = ("KA", "SHI") if balance > 0 else ("SHI", "KA")

                ShiwakeMeisai.objects.create(
                    denpyo=kessan_denpyo,
                    row_no=row,
                    kari_kashi=kk1,
                    kamoku=kamoku,
                    kingaku=abs(balance),
                    tekyou="Closing Entry",
                )
                row += 1
                ShiwakeMeisai.objects.create(
                    denpyo=kessan_denpyo,
                    row_no=row,
                    kari_kashi=kk2,
                    kamoku=retained_earnings,
                    kingaku=abs(balance),
                    tekyou=f"Closing Entry ({kamoku.name})",
                )
                row += 1

            messages.success(
                request,
                f"決算整理仕訳伝票（{kessan_denpyo.denpyo_no}）を作成しました。",
            )
        return redirect("journal:nenji-kessan")

    def get_fiscal_year_list(self):
        """Return list of available fiscal years"""
        year = timezone.now().year
        return range(2025, year + 2)
