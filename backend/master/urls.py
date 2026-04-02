from django.urls import path

from . import views

app_name = "master"

urlpatterns = [
    # 勘定科目マスタ
    path("kanjo/", views.KanjoKamokuListView.as_view(), name="kanjo-list"),
    path("kanjo/new/", views.KanjoKamokuCreateView.as_view(), name="kanjo-create"),
    path(
        "kanjo/<int:pk>/edit/",
        views.KanjoKamokuUpdateView.as_view(),
        name="kanjo-update",
    ),
    path(
        "kanjo/<int:pk>/delete/",
        views.KanjoKamokuDeleteView.as_view(),
        name="kanjo-delete",
    ),
    # 部門マスタ
    path("bumon/", views.BumonListView.as_view(), name="bumon-list"),
    path("bumon/new/", views.BumonCreateView.as_view(), name="bumon-create"),
    path("bumon/<int:pk>/edit/", views.BumonUpdateView.as_view(), name="bumon-update"),
    path(
        "bumon/<int:pk>/delete/", views.BumonDeleteView.as_view(), name="bumon-delete"
    ),
    # 消費税率マスタ
    path("zei/", views.ZeiListView.as_view(), name="zei-list"),
    path("zei/new/", views.ZeiCreateView.as_view(), name="zei-create"),
    path("zei/<int:pk>/edit/", views.ZeiUpdateView.as_view(), name="zei-update"),
    path("zei/<int:pk>/delete/", views.ZeiDeleteView.as_view(), name="zei-delete"),
    # 取引先マスタ
    path("torihiki/", views.TorihikiSakiListView.as_view(), name="torihiki-list"),
    path(
        "torihiki/new/", views.TorihikiSakiCreateView.as_view(), name="torihiki-create"
    ),
    path(
        "torihiki/<int:pk>/edit/",
        views.TorihikiSakiUpdateView.as_view(),
        name="torihiki-update",
    ),
    path(
        "torihiki/<int:pk>/delete/",
        views.TorihikiSakiDeleteView.as_view(),
        name="torihiki-delete",
    ),
]
