# =========================================================
# Master URLs
# =========================================================

from django.urls import path

from . import views

app_name = "master"

urlpatterns = [
    # Account Master
    path("kanjo/", views.KanjoKamokuListView.as_view(), name="kanjo-list"),
    path("kanjo/new/", views.KanjoKamokuCreateView.as_view(), name="kanjo-create"),
    path("kanjo/<int:pk>/edit/", views.KanjoKamokuUpdateView.as_view(), name="kanjo-update"),
    path("kanjo/<int:pk>/delete/", views.KanjoKamokuDeleteView.as_view(), name="kanjo-delete"),
    # Sub-account Master
    path("hojo/", views.HojoKamokuListView.as_view(), name="hojo-list"),
    path("hojo/new/", views.HojoKamokuCreateView.as_view(), name="hojo-create"),
    path("hojo/<int:pk>/edit/", views.HojoKamokuUpdateView.as_view(), name="hojo-update"),
    path("hojo/<int:pk>/delete/", views.HojoKamokuDeleteView.as_view(), name="hojo-delete"),
    # Department Master
    path("bumon/", views.BumonListView.as_view(), name="bumon-list"),
    path("bumon/new/", views.BumonCreateView.as_view(), name="bumon-create"),
    path("bumon/<int:pk>/edit/", views.BumonUpdateView.as_view(), name="bumon-update"),
    path("bumon/<int:pk>/delete/", views.BumonDeleteView.as_view(), name="bumon-delete"),
    # Tax Master
    path("zei/", views.ZeiListView.as_view(), name="zei-list"),
    path("zei/new/", views.ZeiCreateView.as_view(), name="zei-create"),
    path("zei/<int:pk>/edit/", views.ZeiUpdateView.as_view(), name="zei-update"),
    path("zei/<int:pk>/delete/", views.ZeiDeleteView.as_view(), name="zei-delete"),
    # Business Partner Master (Customers / Suppliers)
    path("torihiki/", views.TorihikiSakiListView.as_view(), name="torihiki-list"),
    path("torihiki/new/", views.TorihikiSakiCreateView.as_view(), name="torihiki-create"),
    path("torihiki/<int:pk>/edit/", views.TorihikiSakiUpdateView.as_view(), name="torihiki-update"),
    path("torihiki/<int:pk>/delete/", views.TorihikiSakiDeleteView.as_view(), name="torihiki-delete"),
    # Journal Dictionary (仕訳辞書)
    path("dict/", views.ShiwakeDictionaryListView.as_view(), name="dict-list"),
    path("dict/new/", views.ShiwakeDictionaryCreateView.as_view(), name="dict-create"),
    path("dict/<int:pk>/edit/", views.ShiwakeDictionaryUpdateView.as_view(), name="dict-update"),
    path("dict/<int:pk>/delete/", views.ShiwakeDictionaryDeleteView.as_view(), name="dict-delete"),
]
