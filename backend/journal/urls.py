# =========================================================
# Journal URLs
# =========================================================

from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    # Journal Ledger
    path("", views.DenpyoListView.as_view(), name="denpyo-list"),
    path("new/", views.DenpyoCreateView.as_view(), name="denpyo-create"),
    path("<int:pk>/edit/", views.DenpyoUpdateView.as_view(), name="denpyo-update"),
    path("<int:pk>/delete/", views.DenpyoDeleteView.as_view(), name="denpyo-delete"),
    # Monthly closing
    path("shime/", views.GetsujiShimeListView.as_view(), name="getsuji-shime"),
    path("shime/toggle/", views.GetsujiShimeToggleView.as_view(), name="getsuji-shime-toggle"),
    # Year-end closing
    path("closing/", views.NenjiKessanView.as_view(), name="nenji-kessan"),
    # HTMX endpoints
    path("htmx/add-row/", views.add_meisai_row, name="add-row"),
    path("htmx/balance-check/", views.balance_check, name="balance-check"),
]
