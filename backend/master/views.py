from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BumonForm, KanjoKamokuForm, TorihikiSakiForm, ZeiForm
from .models import BumonMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster


# =========================================================
# ミックスイン: HTMX対応 モーダルレスポンス
# =========================================================
class HtmxModalMixin:
    """HTMXリクエスト時はモーダル部分テンプレートを返す"""

    modal_template = None

    def get_modal_template(self):
        return self.modal_template

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            messages.success(self.request, f"「{self.object}」を保存しました。")
            return HttpResponse(
                "",
                status=200,
                headers={"HX-Trigger": "refreshList"},
            )
        return response

    def form_invalid(self, form):
        if self.request.htmx:
            return render(
                self.request,
                self.get_modal_template(),
                self.get_context_data(form=form),
            )
        return super().form_invalid(form)


class HtmxListMixin:
    """HTMXリクエスト時は部分テンプレートを返す"""

    partial_template_name = None

    def get_template_names(self):
        if self.request.htmx:
            return [self.partial_template_name]
        return [self.template_name]


# =========================================================
# 勘定科目マスタ
# =========================================================
class KanjoKamokuListView(LoginRequiredMixin, HtmxListMixin, ListView):
    model = KanjoKamokuMaster
    template_name = "master/kanjo_list.html"
    partial_template_name = "master/partials/kanjo_table.html"
    context_object_name = "kamoku_list"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        level = self.request.GET.get("level", "")
        taisha = self.request.GET.get("taisha", "")
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        if level:
            qs = qs.filter(level=level)
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


class KanjoKamokuCreateView(LoginRequiredMixin, HtmxModalMixin, CreateView):
    model = KanjoKamokuMaster
    form_class = KanjoKamokuForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:kanjo-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "勘定科目 新規登録"
        ctx["action_url"] = reverse_lazy("master:kanjo-create")
        return ctx


class KanjoKamokuUpdateView(LoginRequiredMixin, HtmxModalMixin, UpdateView):
    model = KanjoKamokuMaster
    form_class = KanjoKamokuForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:kanjo-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"勘定科目 編集: {self.object}"
        ctx["action_url"] = reverse_lazy("master:kanjo-update", args=[self.object.pk])
        return ctx


class KanjoKamokuDeleteView(LoginRequiredMixin, DeleteView):
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
            from django.shortcuts import redirect

            return redirect(self.success_url)
        except ProtectedError:
            messages.error(
                self.request, "この科目はすでに仕訳に使用されているため削除できません。"
            )
            if self.request.htmx:
                return HttpResponse(status=409)
            return self.get(self.request)


# =========================================================
# 部門マスタ
# =========================================================
class BumonListView(LoginRequiredMixin, HtmxListMixin, ListView):
    model = BumonMaster
    template_name = "master/bumon_list.html"
    partial_template_name = "master/partials/bumon_table.html"
    context_object_name = "bumon_list"

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        return qs


class BumonCreateView(LoginRequiredMixin, HtmxModalMixin, CreateView):
    model = BumonMaster
    form_class = BumonForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:bumon-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "部門 新規登録"
        ctx["action_url"] = reverse_lazy("master:bumon-create")
        return ctx


class BumonUpdateView(LoginRequiredMixin, HtmxModalMixin, UpdateView):
    model = BumonMaster
    form_class = BumonForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:bumon-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"部門 編集: {self.object}"
        ctx["action_url"] = reverse_lazy("master:bumon-update", args=[self.object.pk])
        return ctx


class BumonDeleteView(LoginRequiredMixin, DeleteView):
    model = BumonMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:bumon-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy("master:bumon-delete", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        obj = self.get_object()
        name = str(obj)
        obj.delete()
        messages.success(self.request, f"「{name}」を削除しました。")
        if self.request.htmx:
            return HttpResponse("", status=200, headers={"HX-Trigger": "refreshList"})
        from django.shortcuts import redirect

        return redirect(self.success_url)

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
                return HttpResponse(
                    "", status=200, headers={"HX-Trigger": "refreshList"}
                )
            from django.shortcuts import redirect

            return redirect(self.success_url)
        except ProtectedError:
            messages.error(
                self.request, "この部門はすでに使用されているため削除できません。"
            )
            if self.request.htmx:
                return HttpResponse(status=409)
            return self.get(self.request)


# =========================================================
# 消費税率マスタ
# =========================================================
class ZeiListView(LoginRequiredMixin, HtmxListMixin, ListView):
    model = ZeiMaster
    template_name = "master/zei_list.html"
    partial_template_name = "master/partials/zei_table.html"
    context_object_name = "zei_list"


class ZeiCreateView(LoginRequiredMixin, HtmxModalMixin, CreateView):
    model = ZeiMaster
    form_class = ZeiForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:zei-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "税区分 新規登録"
        ctx["action_url"] = reverse_lazy("master:zei-create")
        return ctx


class ZeiUpdateView(LoginRequiredMixin, HtmxModalMixin, UpdateView):
    model = ZeiMaster
    form_class = ZeiForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:zei-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"税区分 編集: {self.object}"
        ctx["action_url"] = reverse_lazy("master:zei-update", args=[self.object.pk])
        return ctx


class ZeiDeleteView(LoginRequiredMixin, DeleteView):
    model = ZeiMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:zei-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy("master:zei-delete", args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        obj = self.get_object()
        name = str(obj)
        obj.delete()
        messages.success(self.request, f"「{name}」を削除しました。")
        if self.request.htmx:
            return HttpResponse("", status=200, headers={"HX-Trigger": "refreshList"})
        from django.shortcuts import redirect

        return redirect(self.success_url)


# =========================================================
# 取引先マスタ
# =========================================================
class TorihikiSakiListView(LoginRequiredMixin, HtmxListMixin, ListView):
    model = TorihikiSakiMaster
    template_name = "master/torihiki_list.html"
    partial_template_name = "master/partials/torihiki_table.html"
    context_object_name = "torihiki_list"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(code__icontains=q) | qs.filter(name__icontains=q)
        return qs


class TorihikiSakiCreateView(LoginRequiredMixin, HtmxModalMixin, CreateView):
    model = TorihikiSakiMaster
    form_class = TorihikiSakiForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:torihiki-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "取引先 新規登録"
        ctx["action_url"] = reverse_lazy("master:torihiki-create")
        return ctx


class TorihikiSakiUpdateView(LoginRequiredMixin, HtmxModalMixin, UpdateView):
    model = TorihikiSakiMaster
    form_class = TorihikiSakiForm
    template_name = "master/partials/form_modal.html"
    modal_template = "master/partials/form_modal.html"
    success_url = reverse_lazy("master:torihiki-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"取引先 編集: {self.object}"
        ctx["action_url"] = reverse_lazy(
            "master:torihiki-update", args=[self.object.pk]
        )
        return ctx


class TorihikiSakiDeleteView(LoginRequiredMixin, DeleteView):
    model = TorihikiSakiMaster
    template_name = "master/partials/delete_confirm.html"
    success_url = reverse_lazy("master:torihiki-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["delete_url"] = reverse_lazy(
            "master:torihiki-delete", args=[self.object.pk]
        )
        return ctx

    def form_valid(self, form):
        obj = self.get_object()
        name = str(obj)
        obj.delete()
        messages.success(self.request, f"「{name}」を削除しました。")
        if self.request.htmx:
            return HttpResponse("", status=200, headers={"HX-Trigger": "refreshList"})
        from django.shortcuts import redirect

        return redirect(self.success_url)
