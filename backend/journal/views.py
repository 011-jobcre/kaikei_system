import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import MeisaiFormSet, ShiwakeDenpyoForm, ShiwakeMeisaiForm
from .models import ShiwakeDenpyo


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
            messages.success(self.request, f"伝票 {self.object.denpyo_no} を保存しました。")
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


# -------------------------------------------------------
# Journal Ledger - List
# -------------------------------------------------------
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


# -------------------------------------------------------
# Voucher / Create Entry
# -------------------------------------------------------
class DenpyoCreateView(LoginRequiredMixin, HtmxModalMixin, CreateView):
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

        return super().form_valid(form)


# -------------------------------------------------------
# Voucher / Edit Entry
# -------------------------------------------------------
class DenpyoUpdateView(LoginRequiredMixin, HtmxModalMixin, UpdateView):
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
                return render(self.request, self.template_name, self.get_context_data())
            return redirect(self.success_url)
        no = denpyo.denpyo_no
        denpyo.delete()
        messages.success(self.request, f"伝票 {no} を削除しました。")
        if self.request.htmx:
            return HttpResponse(
                "",
                status=200,
                headers={"HX-Redirect": str(self.success_url)},
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
