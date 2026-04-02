from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    # 仕訳日記帳
    path("", views.DenpyoListView.as_view(), name="denpyo-list"),
    path("new/", views.DenpyoCreateView.as_view(), name="denpyo-create"),
    path("<int:pk>/edit/", views.DenpyoUpdateView.as_view(), name="denpyo-update"),
    path("<int:pk>/delete/", views.DenpyoDeleteView.as_view(), name="denpyo-delete"),
    # HTMX エンドポイント
    path("htmx/add-row/", views.add_meisai_row, name="add-row"),
    path("htmx/balance-check/", views.balance_check, name="balance-check"),
]
