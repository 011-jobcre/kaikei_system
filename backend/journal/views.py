import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, ListView

from .forms import MeisaiFormSet, ShiwakeDenpyoForm, ShiwakeMeisaiForm
from .models import ShiwakeDenpyo, ShiwakeMeisai


# -------------------------------------------------------
# Journal Ledger - List
# -------------------------------------------------------
class DenpyoListView(LoginRequiredMixin, ListView):
    model = ShiwakeDenpyo
    template_name = "journal/denpyo_list.html"
    context_object_name = "denpyo_list"
    paginate_by = 30

    def get_queryset(self):
        qs = ShiwakeDenpyo.objects.select_related("created_by").prefetch_related(
            "meisai__kamoku"
        )
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


# -------------------------------------------------------
# Voucher / Create Entry
# -------------------------------------------------------
class DenpyoCreateView(LoginRequiredMixin, View):
    template_name = "journal/denpyo_form.html"

    def get(self, request):
        form = ShiwakeDenpyoForm()
        formset = MeisaiFormSet()
        context = {
            "form": form,
            "formset": formset,
            "title": "振替伝票 新規作成",
            "is_new": True,
        }
        if request.htmx:
            return render(request, "journal/partials/denpyo_form_modal.html", context)
        return render(request, self.template_name, context)

    def post(self, request):
        form = ShiwakeDenpyoForm(request.POST)
        formset = MeisaiFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                denpyo = form.save(commit=False)
                denpyo.created_by = request.user
                denpyo.save()
                formset.instance = denpyo
                formset.save()
            messages.success(request, f"伝票 {denpyo.denpyo_no} を登録しました。")
            if request.htmx:
                return HttpResponse(
                    "",
                    status=200,
                    headers={"HX-Trigger": "refreshList"},
                )
            return redirect("journal:denpyo-list")

        context = {
            "form": form,
            "formset": formset,
            "title": "振替伝票 新規作成",
            "is_new": True,
        }
        if request.htmx:
            return render(request, "journal/partials/denpyo_form_modal.html", context)
        return render(request, self.template_name, context)


# -------------------------------------------------------
# Voucher / Edit Entry
# -------------------------------------------------------
class DenpyoUpdateView(LoginRequiredMixin, View):
    template_name = "journal/denpyo_form.html"

    def get_object(self, pk):
        return get_object_or_404(ShiwakeDenpyo, pk=pk)

    def get(self, request, pk):
        denpyo = self.get_object(pk)
        if denpyo.is_locked:
            messages.error(request, "この伝票はロックされており編集できません。")
            return redirect("journal:denpyo-list")
        form = ShiwakeDenpyoForm(instance=denpyo)
        formset = MeisaiFormSet(instance=denpyo)
        context = {
            "form": form,
            "formset": formset,
            "denpyo": denpyo,
            "title": f"振替伝票 編集: {denpyo.denpyo_no}",
            "is_new": False,
        }
        if request.htmx:
            return render(request, "journal/partials/denpyo_form_modal.html", context)
        return render(request, self.template_name, context)

    def post(self, request, pk):
        denpyo = self.get_object(pk)
        if denpyo.is_locked:
            messages.error(request, "ロックされた伝票は編集できません。")
            if request.htmx:
                return HttpResponse(status=409)
            return redirect("journal:denpyo-list")

        form = ShiwakeDenpyoForm(request.POST, instance=denpyo)
        formset = MeisaiFormSet(request.POST, instance=denpyo)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, f"伝票 {denpyo.denpyo_no} を更新しました。")
            if request.htmx:
                return HttpResponse(
                    "",
                    status=200,
                    headers={"HX-Trigger": "refreshList"},
                )
            return redirect("journal:denpyo-list")

        if request.htmx:
            context = {
                "form": form,
                "formset": formset,
                "denpyo": denpyo,
                "title": f"振替伝票 編集: {denpyo.denpyo_no}",
                "is_new": False,
            }
            return render(request, "journal/partials/denpyo_form_modal.html", context)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "denpyo": denpyo,
                "title": f"振替伝票 編集: {denpyo.denpyo_no}",
                "is_new": False,
            },
        )


# -------------------------------------------------------
# Voucher / Delete Entry
# -------------------------------------------------------
class DenpyoDeleteView(LoginRequiredMixin, DeleteView):
    model = ShiwakeDenpyo
    template_name = "journal/partials/delete_confirm.html"
    success_url = reverse_lazy("journal:denpyo-list")

    def form_valid(self, form):
        denpyo = self.get_object()
        if denpyo.is_locked:
            messages.error(self.request, "ロックされた伝票は削除できません。")
            if self.request.htmx:
                return HttpResponse(status=409)
            return redirect("journal:denpyo-list")
        no = denpyo.denpyo_no
        denpyo.delete()
        messages.success(self.request, f"伝票 {no} を削除しました。")
        if self.request.htmx:
            return HttpResponse(
                "",
                status=200,
                headers={"HX-Trigger": "refreshList"},
            )
        return redirect(self.success_url)


# -------------------------------------------------------
# HTMX: Add one detail row
# -------------------------------------------------------
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


# -------------------------------------------------------
# HTMX: Real-time debit/credit difference check
# -------------------------------------------------------
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
