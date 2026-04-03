from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import render
from django.views import View

from journal.models import ShiwakeMeisai
from master.models import KanjoKamokuMaster


def _aggregate_by_kubun(kubun_list, date_to=None):
    """Aggregate debit/credit occurrences for the given account-type group and return balance (zandaka)."""
    qs = ShiwakeMeisai.objects.filter(kamoku__taisha_kubun__in=kubun_list)
    if date_to:
        qs = qs.filter(denpyo__hiduke__lte=date_to)
    agg = qs.aggregate(
        kari=models.Sum("kingaku", filter=models.Q(kari_kashi="KA")),
        kashi=models.Sum("kingaku", filter=models.Q(kari_kashi="SHI")),
    )
    return agg["kari"] or Decimal("0"), agg["kashi"] or Decimal("0")


class BalanceSheetView(LoginRequiredMixin, View):
    """Balance Sheet (B/S)"""

    template_name = "report/balance_sheet.html"

    def get(self, request):
        date_to = request.GET.get("date_to", "")

        # Assets
        shisan_kamoku = KanjoKamokuMaster.objects.filter(
            taisha_kubun="SHISAN", level=4, is_active=True
        ).order_by("code")
        shisan_rows = []
        total_shisan = Decimal("0")
        for k in shisan_kamoku:
            qs = ShiwakeMeisai.objects.filter(kamoku=k)
            if date_to:
                qs = qs.filter(denpyo__hiduke__lte=date_to)
            agg = qs.aggregate(
                kari=models.Sum("kingaku", filter=models.Q(kari_kashi="KA")),
                kashi=models.Sum("kingaku", filter=models.Q(kari_kashi="SHI")),
            )
            z = (agg["kari"] or Decimal("0")) - (agg["kashi"] or Decimal("0"))
            if z != 0:
                shisan_rows.append({"kamoku": k, "zandaka": z})
                total_shisan += z

        # Liabilities
        fusai_rows, total_fusai = self._get_rows("FUSAI", date_to)
        # Equity
        junshisan_rows, total_junshisan = self._get_rows("JUNSHISAN", date_to)

        return render(
            request,
            self.template_name,
            {
                "shisan_rows": shisan_rows,
                "total_shisan": total_shisan,
                "fusai_rows": fusai_rows,
                "total_fusai": total_fusai,
                "junshisan_rows": junshisan_rows,
                "total_junshisan": total_junshisan,
                "total_fusai_junshisan": total_fusai + total_junshisan,
                "balanced": total_shisan == total_fusai + total_junshisan,
                "date_to": date_to,
            },
        )

    def _get_rows(self, taisha_kubun, date_to):
        kamoku_qs = KanjoKamokuMaster.objects.filter(
            taisha_kubun=taisha_kubun, level=4, is_active=True
        ).order_by("code")
        rows = []
        total = Decimal("0")
        for k in kamoku_qs:
            qs = ShiwakeMeisai.objects.filter(kamoku=k)
            if date_to:
                qs = qs.filter(denpyo__hiduke__lte=date_to)
            agg = qs.aggregate(
                kari=models.Sum("kingaku", filter=models.Q(kari_kashi="KA")),
                kashi=models.Sum("kingaku", filter=models.Q(kari_kashi="SHI")),
            )
            z = (agg["kashi"] or Decimal("0")) - (agg["kari"] or Decimal("0"))
            if z != 0:
                rows.append({"kamoku": k, "zandaka": z})
                total += z
        return rows, total


class IncomeStatementView(LoginRequiredMixin, View):
    """Income Statement (P/L)"""

    template_name = "report/income_statement.html"

    def get(self, request):
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")

        def get_rows(taisha_kubun, is_kari_zandaka):
            qs_k = KanjoKamokuMaster.objects.filter(
                taisha_kubun=taisha_kubun, level=4, is_active=True
            ).order_by("code")
            rows = []
            total = Decimal("0")
            for k in qs_k:
                qs = ShiwakeMeisai.objects.filter(kamoku=k)
                if date_from:
                    qs = qs.filter(denpyo__hiduke__gte=date_from)
                if date_to:
                    qs = qs.filter(denpyo__hiduke__lte=date_to)
                agg = qs.aggregate(
                    kari=models.Sum("kingaku", filter=models.Q(kari_kashi="KA")),
                    kashi=models.Sum("kingaku", filter=models.Q(kari_kashi="SHI")),
                )
                ka = agg["kari"] or Decimal("0")
                sh = agg["kashi"] or Decimal("0")
                z = (ka - sh) if is_kari_zandaka else (sh - ka)
                if z != 0:
                    rows.append({"kamoku": k, "zandaka": z})
                    total += z
            return rows, total

        shueki_rows, total_shueki = get_rows("SHUEKI", False)
        hiyo_rows, total_hiyo = get_rows("HIYO", True)
        rieki = total_shueki - total_hiyo

        return render(
            request,
            self.template_name,
            {
                "shueki_rows": shueki_rows,
                "total_shueki": total_shueki,
                "hiyo_rows": hiyo_rows,
                "total_hiyo": total_hiyo,
                "rieki": rieki,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
