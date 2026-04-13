# =========================================================
# Ledger URLs
# =========================================================

from django.urls import path
from .views import (
    SokanjoMotochoView,
    HojoMotochoView,
    GenkinSuitouchoView,
    ZandakaShisanhyouView,
    ZandakaExportView,
)

app_name = "ledger"

urlpatterns = [
    # General Ledger
    path("sokanjo/", SokanjoMotochoView.as_view(), name="sokanjo"),
    # Sub-ledger
    path("hojo/", HojoMotochoView.as_view(), name="hojo"),
    # Cash Book
    path("genkin/", GenkinSuitouchoView.as_view(), name="genkin"),
    # Trial Balance
    path("zandaka/", ZandakaShisanhyouView.as_view(), name="zandaka"),
    path("zandaka/export/<str:fmt>/", ZandakaExportView.as_view(), name="zandaka-export"),
]
