# =========================================================
# Master Views
# =========================================================

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from common.permissions import AdminRequiredMixin

from .forms import KanjoKamokuForm, HojoKamokuForm, BumonForm, TorihikiSakiForm, ZeiForm
from .models import KanjoKamokuMaster, HojoKamokuMaster, BumonMaster, TorihikiSakiMaster, ZeiMaster


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


class BaseMasterDeleteView(AdminRequiredMixin, DeleteView):
    """Base DeleteView for master data with ProtectedError handling and HTMX support."""

    delete_error_message = "このデータはすでに使用されているため削除できません。"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy(f"{self.url_name_prefix}-delete", args=[self.object.pk])
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
            messages.error(self.request, self.delete_error_message)
            if self.request.htmx:
                return render(self.request, self.template_name, self.get_context_data())
            return self.get(self.request)


class BaseMasterModalView(AdminRequiredMixin, HtmxModalMixin):
    """Base class for Create/Update views with modal context."""

    model_name_ja = None  # Japanese model name (e.g., "勘定科目")
    url_name_prefix = None  # URL name prefix (e.g., "kanjo")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if isinstance(self, UpdateView):
            ctx["title"] = f"{self.model_name_ja} 編集: {self.object}"
            ctx["action_url"] = reverse_lazy(f"{self.url_name_prefix}-update", args=[self.object.pk])
        else:
            ctx["title"] = f"{self.model_name_ja} 新規登録"
            ctx["action_url"] = reverse_lazy(f"{self.url_name_prefix}-create")
        return ctx


class BaseMasterListView(LoginRequiredMixin, HtmxListMixin, ListView):
    """Base ListView with common search filter logic."""

    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


# =========================================================
# Account Master
# =========================================================


class KanjoKamokuListView(BaseMasterListView):
    """
    Displays the full account master with optional filters:
    - q          : search by code or account name
    - level      : filter by hierarchy level (1=large … 4=detail)
    - taisha     : filter by debit/credit classification
    """

    model = KanjoKamokuMaster
    template_name = "master/kanjo_list.html"
    partial_template_name = "master/partials/kanjo_list_table.html"
    context_object_name = "kamoku_list"

    def get_queryset(self):
        level = self.request.GET.get("level", "")
        taisha = self.request.GET.get("taisha", "")
        qs = super().get_queryset()
        if level:
            qs = qs.filter(level=level)
        if taisha:
            qs = qs.filter(taisha_kubun=taisha)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["taisha_choices"] = KanjoKamokuMaster.TAISHA_KUBUN_CHOICES
        ctx["level_filter"] = self.request.GET.get("level", "")
        ctx["taisha_filter"] = self.request.GET.get("taisha", "")
        return ctx


class KanjoKamokuCreateView(BaseMasterModalView, CreateView):
    """Modal form to create a new account."""

    model = KanjoKamokuMaster
    form_class = KanjoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:kanjo-list")
    action_name = "新規登録"
    model_name_ja = "勘定科目"
    url_name_prefix = "master:kanjo"


class KanjoKamokuUpdateView(BaseMasterModalView, UpdateView):
    """Modal form to edit an existing account."""

    model = KanjoKamokuMaster
    form_class = KanjoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:kanjo-list")
    action_name = "更新"
    model_name_ja = "勘定科目"
    url_name_prefix = "master:kanjo"


class KanjoKamokuDeleteView(BaseMasterDeleteView):
    """Confirms and processes deletion of a account."""

    model = KanjoKamokuMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:kanjo-list")
    url_name_prefix = "master:kanjo"
    delete_error_message = "この科目はすでに仕訳に使用されているため削除できません。"


# =========================================================
# Sub-account Master
# =========================================================


class HojoKamokuListView(BaseMasterListView):
    """List all sub-accounts with optional filters by parent account or keyword."""

    model = HojoKamokuMaster
    template_name = "master/hojo_list.html"
    partial_template_name = "master/partials/hojo_list_table.html"
    context_object_name = "hojo_list"

    def get_queryset(self):
        qs = HojoKamokuMaster.objects.select_related("kamoku")
        kamoku_id = self.request.GET.get("kamoku", "")
        if kamoku_id:
            qs = qs.filter(kamoku_id=kamoku_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kamoku_id"] = self.request.GET.get("kamoku", "")
        ctx["kamoku_choices"] = KanjoKamokuMaster.objects.filter(level=4, is_active=True).order_by("code")
        return ctx


class HojoKamokuCreateView(BaseMasterModalView, CreateView):
    """Modal form to create a new sub-account."""

    model = HojoKamokuMaster
    form_class = HojoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:hojo-list")
    action_name = "新規登録"
    model_name_ja = "補助科目"
    url_name_prefix = "master:hojo"


class HojoKamokuUpdateView(BaseMasterModalView, UpdateView):
    """Modal form to edit an existing sub-account."""

    model = HojoKamokuMaster
    form_class = HojoKamokuForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:hojo-list")
    action_name = "更新"
    model_name_ja = "補助科目"
    url_name_prefix = "master:hojo"


class HojoKamokuDeleteView(BaseMasterDeleteView):
    """Confirms and processes deletion of a sub-account."""

    model = HojoKamokuMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:hojo-list")
    url_name_prefix = "master:hojo"
    delete_error_message = "この補助科目はすでに仕訳に使用されているため削除できません。"


# =========================================================
# Department Master
# =========================================================


class BumonListView(BaseMasterListView):
    """Lists all departments with an optional code/name keyword search."""

    model = BumonMaster
    template_name = "master/bumon_list.html"
    partial_template_name = "master/partials/bumon_list_table.html"
    context_object_name = "bumon_list"


class BumonCreateView(BaseMasterModalView, CreateView):
    """Modal form to create a new department."""

    model = BumonMaster
    form_class = BumonForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:bumon-list")
    action_name = "新規登録"
    model_name_ja = "部門"
    url_name_prefix = "master:bumon"


class BumonUpdateView(BaseMasterModalView, UpdateView):
    """Modal form to edit an existing department."""

    model = BumonMaster
    form_class = BumonForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:bumon-list")
    action_name = "更新"
    model_name_ja = "部門"
    url_name_prefix = "master:bumon"


class BumonDeleteView(BaseMasterDeleteView):
    """Confirms and processes deletion of a department."""

    model = BumonMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:bumon-list")
    url_name_prefix = "master:bumon"
    delete_error_message = "この部門はすでに使用されているため削除できません。"


# =========================================================
# Tax Rate Master
# =========================================================


class ZeiListView(BaseMasterListView):
    """Lists all tax rates (small dataset — no search filter needed)."""

    model = ZeiMaster
    template_name = "master/zei_list.html"
    partial_template_name = "master/partials/zei_list_table.html"
    context_object_name = "zei_list"

    def get_queryset(self):
        return super().get_queryset()  # No search filter for tax rates


class ZeiCreateView(BaseMasterModalView, CreateView):
    """Modal form to create a new tax rate entry."""

    model = ZeiMaster
    form_class = ZeiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:zei-list")
    action_name = "新規登録"
    model_name_ja = "税区分"
    url_name_prefix = "master:zei"


class ZeiUpdateView(BaseMasterModalView, UpdateView):
    """Modal form to edit an existing tax rate entry."""

    model = ZeiMaster
    form_class = ZeiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:zei-list")
    action_name = "更新"
    model_name_ja = "税区分"
    url_name_prefix = "master:zei"


class ZeiDeleteView(BaseMasterDeleteView):
    """Confirms and processes deletion of a tax rate."""

    model = ZeiMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:zei-list")
    url_name_prefix = "master:zei"
    delete_error_message = "この税区分はすでに仕訳に使用されているため削除できません。"


# =========================================================
# Business Partner Master
# =========================================================


class TorihikiSakiListView(BaseMasterListView):
    """Lists business partners (customers / suppliers) with code/name search."""

    model = TorihikiSakiMaster
    template_name = "master/torihiki_list.html"
    partial_template_name = "master/partials/torihiki_list_table.html"
    context_object_name = "torihiki_list"


class TorihikiSakiCreateView(BaseMasterModalView, CreateView):
    """Modal form to create a new business partner."""

    model = TorihikiSakiMaster
    form_class = TorihikiSakiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:torihiki-list")
    action_name = "新規登録"
    model_name_ja = "取引先"
    url_name_prefix = "master:torihiki"


class TorihikiSakiUpdateView(BaseMasterModalView, UpdateView):
    """Modal form to edit an existing business partner."""

    model = TorihikiSakiMaster
    form_class = TorihikiSakiForm
    template_name = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:torihiki-list")
    action_name = "更新"
    model_name_ja = "取引先"
    url_name_prefix = "master:torihiki"


class TorihikiSakiDeleteView(BaseMasterDeleteView):
    """Confirms and processes deletion of a business partner."""

    model = TorihikiSakiMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:torihiki-list")
    url_name_prefix = "master:torihiki"
    delete_error_message = "この取引先はすでに仕訳に使用されているため削除できません。"
