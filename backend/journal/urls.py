# =========================================================
# Journal URLs
# =========================================================

from django.urls import path
from . import views

app_name = "journal"

urlpatterns = [
    # ─── 仕訳一覧 (Shiwake Ichiran — Unified List) ──────────────────
    path("", views.ShiwakeIchiranView.as_view(), name="shiwake-list"),
    # ─── 仕訳日記帳 (Shiwake Nikki — Complex N:N Entry) ────────────
    path("shiwake/new/", views.ShiwakeNikkiCreateView.as_view(), name="shiwake-create"),
    path("shiwake/<int:pk>/edit/", views.ShiwakeNikkiUpdateView.as_view(), name="shiwake-update"),
    # ─── 振替伝票 (Furikae Denpyo — Simple 1:1 Transfer) ───────────
    path("furikae/new/", views.FurikaeDenpyoCreateView.as_view(), name="furikae-create"),
    path("furikae/<int:pk>/edit/", views.FurikaeDenpyoUpdateView.as_view(), name="furikae-update"),
    # ─── 削除 (Delete — shared for both types) ──────────────────────
    path("<int:pk>/delete/", views.DenpyoDeleteView.as_view(), name="denpyo-delete"),
    # ─── 月次締処理 (Monthly Closing) ──────────────────────────────
    path("shime/", views.GetsujiShimeListView.as_view(), name="getsuji-shime"),
    path("shime/toggle/", views.GetsujiShimeToggleView.as_view(), name="getsuji-shime-toggle"),
    # ─── 年次決算 (Year-End Closing) ───────────────────────────────
    path("closing/", views.NenjiKessanView.as_view(), name="nenji-kessan"),
    # ─── HTMX Endpoints ────────────────────────────────────────────
    path("htmx/add-row/", views.add_meisai_row, name="add-row"),
    path("htmx/balance-check/", views.balance_check, name="balance-check"),
]
