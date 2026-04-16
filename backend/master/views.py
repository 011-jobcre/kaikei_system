from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from common.permissions import AdminRequiredMixin

from .forms import BumonForm, HojoKamokuForm, KanjoKamokuForm, TorihikiSakiForm, ZeiForm
from .models import BumonMaster, HojoKamokuMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster


# =========================================================
# Mixins: shared HTMX behaviour for master data views
# =========================================================


class HtmxModalMixin:
    """
    Mixin for Create/Update views that are triggered by HTMX from a modal dialog.

    On success  → returns an empty 200 response with HX-Trigger: refreshList,
                  which signals the list partial to reload itself via HTMX.
    On failure  → re-renders only the modal template with inline validation errors,
                  so the user can correct them without losing the modal.
    """

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            action = getattr(self, "action_name", "保存")
            messages.success(self.request, f"「{self.object}」を{action}しました。")
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


class HtmxListMixin:
    """
    Mixin for ListView that returns only a table partial when the request
    is driven by HTMX (e.g. triggered by a refreshList event after a modal save).
    Full-page requests get the complete list template as normal.
    """

    partial_template_name = None

    def get_template_names(self):
        if self.request.htmx:
            # Return only the table partial for HTMX-driven refreshes
            return [self.partial_template_name]
        return [self.template_name]


# =========================================================
# Account Master
# =========================================================


class KanjoKamokuListView(LoginRequiredMixin, HtmxListMixin, ListView):
    """
    Displays the full account master with optional filters:
    - q          : search by code or account name
    - level      : filter by hierarchy level (1=large … 4=detail)
    - taisha     : filter by debit/credit classification
    """

    model = KanjoKamokuMaster
    template_name = "master/kanjo_list.html"
    partial_template_name = "master/partials/kanjo_table.html"
    context_object_name = "kamoku_list"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        level = self.request.GET.get("level", "")
        taisha = self.request.GET.get("taisha", "")
        # Full-text search on code OR name
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        # Filter by hierarchy depth
        if level:
            qs = qs.filter(level=level)
        # Filter by debit/credit classification (taisha_kubun)
        if taisha:
            qs = qs.filter(taisha_kubun=taisha)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["taisha_choices"] = KanjoKamokuMaster.TAISHA_KUBUN_CHOICES
        ctx["q"] = self.request.GET.get("q", "")
        ctx["level_filter"] = self.request.GET.get("level", "")
        ctx["taisha_filter"] = self.request.GET.get("taisha", "")
        return ctx


class KanjoKamokuCreateView(AdminRequiredMixin, HtmxModalMixin, CreateView):
    """Modal form to create a new account code entry."""

    model = KanjoKamokuMaster
    form_class = KanjoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:kanjo-list")
    action_name = "新規登録"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "勘定科目 新規登録"
        ctx["action_url"] = reverse_lazy("master:kanjo-create")
        return ctx


class KanjoKamokuUpdateView(AdminRequiredMixin, HtmxModalMixin, UpdateView):
    """Modal form to edit an existing account code entry."""

    model = KanjoKamokuMaster
    form_class = KanjoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:kanjo-list")
    action_name = "更新"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"勘定科目 編集: {self.object}"
        ctx["action_url"] = reverse_lazy("master:kanjo-update", args=[self.object.pk])
        return ctx


class KanjoKamokuDeleteView(AdminRequiredMixin, DeleteView):
    """
    Confirms and processes deletion of an account code.
    Returns HTTP 409 if the account is already referenced by journal entries.
    """

    model = KanjoKamokuMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:kanjo-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy("master:kanjo-delete", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        try:
            obj = self.get_object()
            name = str(obj)
            obj.delete()
            messages.success(self.request, f"「{name}」を削除しました。")
            if self.request.htmx:
                return HttpResponse(
                    "",
                    status=200,
                    headers={"HX-Trigger": "refreshList"},
                )
            return redirect(self.success_url)
        except ProtectedError:
            # The account is linked to journal entries and cannot be deleted
            messages.error(self.request, "この科目はすでに仕訳に使用されているため削除できません。")
            if self.request.htmx:
                return render(self.request, self.template_name, self.get_context_data())
            return self.get(self.request)


# =========================================================
# Department Master
# =========================================================


class BumonListView(LoginRequiredMixin, HtmxListMixin, ListView):
    """Lists all departments with an optional code/name keyword search."""

    model = BumonMaster
    template_name = "master/bumon_list.html"
    partial_template_name = "master/partials/bumon_table.html"
    context_object_name = "bumon_list"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        return qs


class BumonCreateView(AdminRequiredMixin, HtmxModalMixin, CreateView):
    """Modal form to create a new department."""

    model = BumonMaster
    form_class = BumonForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:bumon-list")
    action_name = "新規登録"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "部門 新規登録"
        ctx["action_url"] = reverse_lazy("master:bumon-create")
        return ctx


class BumonUpdateView(AdminRequiredMixin, HtmxModalMixin, UpdateView):
    """Modal form to edit an existing department."""

    model = BumonMaster
    form_class = BumonForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:bumon-list")
    action_name = "更新"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"部門 編集: {self.object}"
        ctx["action_url"] = reverse_lazy("master:bumon-update", args=[self.object.pk])
        return ctx


class BumonDeleteView(AdminRequiredMixin, DeleteView):
    """
    Confirms and processes deletion of a department.
    Returns HTTP 409 if the department is already referenced by journal entries.
    """

    model = BumonMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:bumon-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy("master:bumon-delete", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        try:
            obj = self.get_object()
            name = str(obj)
            obj.delete()
            messages.success(self.request, f"「{name}」を削除しました。")
            if self.request.htmx:
                return HttpResponse("", status=200, headers={"HX-Trigger": "refreshList"})
            return redirect(self.success_url)
        except ProtectedError:
            # The department is linked to journal entries and cannot be deleted
            messages.error(self.request, "この部門はすでに使用されているため削除できません。")
            if self.request.htmx:
                return render(self.request, self.template_name, self.get_context_data())
            return self.get(self.request)


# =========================================================
# Tax Rate Master
# =========================================================


class ZeiListView(LoginRequiredMixin, HtmxListMixin, ListView):
    """Lists all tax rates (small dataset — no search filter needed)."""

    model = ZeiMaster
    template_name = "master/zei_list.html"
    partial_template_name = "master/partials/zei_table.html"
    context_object_name = "zei_list"
    paginate_by = 20


class ZeiCreateView(AdminRequiredMixin, HtmxModalMixin, CreateView):
    """Modal form to create a new tax rate entry."""

    model = ZeiMaster
    form_class = ZeiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:zei-list")
    action_name = "新規登録"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "税区分 新規登録"
        ctx["action_url"] = reverse_lazy("master:zei-create")
        return ctx


class ZeiUpdateView(AdminRequiredMixin, HtmxModalMixin, UpdateView):
    """Modal form to edit an existing tax rate entry."""

    model = ZeiMaster
    form_class = ZeiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:zei-list")
    action_name = "更新"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"税区分 編集: {self.object}"
        ctx["action_url"] = reverse_lazy("master:zei-update", args=[self.object.pk])
        return ctx


class ZeiDeleteView(AdminRequiredMixin, DeleteView):
    """
    Confirms and processes deletion of a tax rate.
    Returns HTTP 409 if it is already referenced by journal entries.
    """

    model = ZeiMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:zei-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy("master:zei-delete", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        try:
            obj = self.get_object()
            name = str(obj)
            obj.delete()
            messages.success(self.request, f"「{name}」を削除しました。")
            if self.request.htmx:
                return HttpResponse("", status=200, headers={"HX-Trigger": "refreshList"})
            return redirect(self.success_url)
        except ProtectedError:
            # The tax rate is referenced by journal entries and cannot be deleted
            messages.error(
                self.request,
                "この税区分はすでに仕訳に使用されているため削除できません。",
            )
            if self.request.htmx:
                return render(self.request, self.template_name, self.get_context_data())
            return self.get(self.request)


# =========================================================
# Business Partner Master
# =========================================================


class TorihikiSakiListView(LoginRequiredMixin, HtmxListMixin, ListView):
    """Lists business partners (customers / suppliers) with code/name search."""

    model = TorihikiSakiMaster
    template_name = "master/torihiki_list.html"
    partial_template_name = "master/partials/torihiki_table.html"
    context_object_name = "torihiki_list"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        return qs


class TorihikiSakiCreateView(AdminRequiredMixin, HtmxModalMixin, CreateView):
    """Modal form to create a new business partner."""

    model = TorihikiSakiMaster
    form_class = TorihikiSakiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:torihiki-list")
    action_name = "新規登録"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "取引先 新規登録"
        ctx["action_url"] = reverse_lazy("master:torihiki-create")
        return ctx


class TorihikiSakiUpdateView(AdminRequiredMixin, HtmxModalMixin, UpdateView):
    """Modal form to edit an existing business partner."""

    model = TorihikiSakiMaster
    form_class = TorihikiSakiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:torihiki-list")
    action_name = "更新"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"取引先 編集: {self.object}"
        ctx["action_url"] = reverse_lazy("master:torihiki-update", args=[self.object.pk])
        return ctx


class TorihikiSakiDeleteView(AdminRequiredMixin, DeleteView):
    """
    Confirms and processes deletion of a business partner.
    Returns HTTP 409 if it is already referenced by journal entries.
    """

    model = TorihikiSakiMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:torihiki-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy("master:torihiki-delete", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        try:
            obj = self.get_object()
            name = str(obj)
            obj.delete()
            messages.success(self.request, f"「{name}」を削除しました。")
            if self.request.htmx:
                return HttpResponse("", status=200, headers={"HX-Trigger": "refreshList"})
            return redirect(self.success_url)
        except ProtectedError:
            # The partner is referenced by journal entries and cannot be deleted
            messages.error(
                self.request,
                "この取引先はすでに仕訳に使用されているため削除できません。",
            )
            if self.request.htmx:
                return render(self.request, self.template_name, self.get_context_data())
            return self.get(self.request)


# =========================================================
# Sub-account Master (補助科目マスタ)
# =========================================================


class HojoKamokuListView(LoginRequiredMixin, HtmxListMixin, ListView):
    """List all sub-accounts with optional filters by parent account or keyword."""

    model = HojoKamokuMaster
    template_name = "master/hojo_list.html"
    partial_template_name = "master/partials/hojo_table.html"
    context_object_name = "hojo_list"
    paginate_by = 30

    def get_queryset(self):
        qs = HojoKamokuMaster.objects.select_related("kamoku")
        q = self.request.GET.get("q", "")
        kamoku_id = self.request.GET.get("kamoku", "")
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        if kamoku_id:
            qs = qs.filter(kamoku_id=kamoku_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["kamoku_id"] = self.request.GET.get("kamoku", "")
        ctx["kamoku_choices"] = KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code")
        return ctx


class HojoKamokuCreateView(AdminRequiredMixin, HtmxModalMixin, CreateView):
    """Modal form to create a new sub-account."""

    model = HojoKamokuMaster
    form_class = HojoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:hojo-list")
    action_name = "新規登録"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "補助科目 新規登録"
        ctx["action_url"] = reverse_lazy("master:hojo-create")
        return ctx


class HojoKamokuUpdateView(AdminRequiredMixin, HtmxModalMixin, UpdateView):
    """Modal form to edit an existing sub-account."""

    model = HojoKamokuMaster
    form_class = HojoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:hojo-list")
    action_name = "更新"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "補助科目 編集"
        ctx["action_url"] = reverse_lazy("master:hojo-update", args=[self.object.pk])
        return ctx


class HojoKamokuDeleteView(AdminRequiredMixin, DeleteView):
    """Confirms and processes deletion of a sub-account."""

    model = HojoKamokuMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:hojo-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy("master:hojo-delete", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        try:
            obj = self.get_object()
            name = str(obj)
            obj.delete()
            messages.success(self.request, f"「{name}」を削除しました。")
            if self.request.htmx:
                return HttpResponse("", status=200, headers={"HX-Trigger": "refreshList"})
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(
                self.request,
                "この補助科目はすでに仕訳に使用されているため削除できません。",
            )
            if self.request.htmx:
                return render(self.request, self.template_name, self.get_context_data())
            return self.get(self.request)
