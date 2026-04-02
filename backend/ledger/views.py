from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from master.models import KanjoKamokuMaster
from journal.models import ShiwakeMeisai


class SokanjoMotochoView(LoginRequiredMixin, View):
    """総勘定元帳 (General Ledger)"""

    template_name = "ledger/sokanjo_motocho.html"

    def get(self, request):
        # Level4の有効科目のみ選択可能
        kamoku_list = KanjoKamokuMaster.objects.filter(
            level=4, is_active=True
        ).order_by("code")

        selected_kamoku = None
        meisai_list = []
        kari_total = Decimal("0")
        kashi_total = Decimal("0")
        zandaka = Decimal("0")

        kamoku_id = request.GET.get("kamoku_id", "")
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")

        if kamoku_id:
            try:
                selected_kamoku = KanjoKamokuMaster.objects.get(pk=kamoku_id, level=4)
                qs = ShiwakeMeisai.objects.filter(
                    kamoku=selected_kamoku
                ).select_related("denpyo", "bumon", "zei_kubun").order_by(
                    "denpyo__hiduke", "denpyo__denpyo_no"
                )
                if date_from:
                    qs = qs.filter(denpyo__hiduke__gte=date_from)
                if date_to:
                    qs = qs.filter(denpyo__hiduke__lte=date_to)

                # 残高の累計計算
                running = Decimal("0")
                for m in qs:
                    if m.kari_kashi == "KA":
                        kari_total += m.kingaku
                        if selected_kamoku.is_kari_zandaka:
                            running += m.kingaku
                        else:
                            running -= m.kingaku
                    else:
                        kashi_total += m.kingaku
                        if selected_kamoku.is_kari_zandaka:
                            running -= m.kingaku
                        else:
                            running += m.kingaku
                    meisai_list.append({
                        "meisai": m,
                        "running_balance": running,
                    })
                zandaka = running
            except KanjoKamokuMaster.DoesNotExist:
                pass

        return render(request, self.template_name, {
            "kamoku_list": kamoku_list,
            "selected_kamoku": selected_kamoku,
            "selected_kamoku_id": kamoku_id,
            "meisai_list": meisai_list,
            "kari_total": kari_total,
            "kashi_total": kashi_total,
            "zandaka": zandaka,
            "date_from": date_from,
            "date_to": date_to,
        })


class ZandakaShisanhyouView(LoginRequiredMixin, View):
    """残高試算表 (Trial Balance)"""

    template_name = "ledger/zandaka_shisanhyou.html"

    def get(self, request):
        date_to = request.GET.get("date_to", "")
        kamoku_list = KanjoKamokuMaster.objects.filter(
            level=4, is_active=True
        ).order_by("code")

        rows = []
        total_kari = Decimal("0")
        total_kashi = Decimal("0")

        for kamoku in kamoku_list:
            qs = ShiwakeMeisai.objects.filter(kamoku=kamoku)
            if date_to:
                qs = qs.filter(denpyo__hiduke__lte=date_to)

            agg = qs.aggregate(
                kari=models.Sum("kingaku", filter=models.Q(kari_kashi="KA")),
                kashi=models.Sum("kingaku", filter=models.Q(kari_kashi="SHI")),
            )
            kari = agg["kari"] or Decimal("0")
            kashi = agg["kashi"] or Decimal("0")

            if kari == 0 and kashi == 0:
                continue  # 発生なし科目はスキップ

            if kamoku.is_kari_zandaka:
                zandaka = kari - kashi
            else:
                zandaka = kashi - kari

            rows.append({
                "kamoku": kamoku,
                "kari_hassei": kari,
                "kashi_hassei": kashi,
                "zandaka": zandaka,
            })
            total_kari += kari
            total_kashi += kashi

        return render(request, self.template_name, {
            "rows": rows,
            "total_kari": total_kari,
            "total_kashi": total_kashi,
            "date_to": date_to,
            "balanced": total_kari == total_kashi,
        })
