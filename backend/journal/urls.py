# =========================================================
# Journal URLs
# =========================================================

from django.urls import path
from . import views

app_name = "journal"

urlpatterns = [
    # 仕訳一覧 (Shiwake List — Unified List)
    path("", views.ShiwakeListView.as_view(), name="shiwake-list"),
    # 仕訳日記帳 (Shiwake Nikki — Spreadsheet Grid View)
    path("shiwake/grid/", views.ShiwakeNikkiCreateView.as_view(), name="shiwake-create"),
    # 振替伝票 (Furikae Denpyo — Complex N:N Entry)
    path("furikae/new/", views.FurikaeDenpyoCreateView.as_view(), name="furikae-create"),
    path("furikae/<int:pk>/edit/", views.FurikaeDenpyoUpdateView.as_view(), name="furikae-update"),
    # 削除 (Delete — shared for both types)
    path("<int:pk>/delete/", views.DenpyoDeleteView.as_view(), name="denpyo-delete"),
    # 月次締処理 (Monthly Closing)
    path("shime/", views.GetsujiShimeListView.as_view(), name="getsuji-shime"),
    path("shime/toggle/", views.GetsujiShimeToggleView.as_view(), name="getsuji-shime-toggle"),
    # 年次決算 (Year-End Closing)
    path("closing/", views.NenjiKessanView.as_view(), name="nenji-kessan"),
    # HTMX Endpoints
    path("htmx/add-form-row/", views.add_form_row, name="add-form-row"),
    path("htmx/shiwake-recent-entries/", views.recent_shiwake_entries, name="shiwake-recent-entries"),
    path("htmx/balance-check/", views.balance_check, name="balance-check"),
]
