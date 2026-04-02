from django.urls import path

from . import views

app_name = "ledger"

urlpatterns = [
    path("sokanjo/", views.SokanjoMotochoView.as_view(), name="sokanjo"),
    path("zandaka/", views.ZandakaShisanhyouView.as_view(), name="zandaka"),
]
