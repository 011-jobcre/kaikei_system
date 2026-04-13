# =========================================================
# Report URLs
# =========================================================

from django.urls import path

from . import views

app_name = "report"

urlpatterns = [
    path("bs/", views.BalanceSheetView.as_view(), name="balance-sheet"),
    path("bs/export/<str:fmt>/", views.BalanceSheetExportView.as_view(), name="bs-export"),
    path("pl/", views.IncomeStatementView.as_view(), name="income-statement"),
    path("pl/export/<str:fmt>/", views.IncomeStatementExportView.as_view(), name="pl-export"),
    path("zei/", views.ZeiSummaryView.as_view(), name="zei-summary"),
    path("zei/export/<str:fmt>/", views.ZeiSummaryExportView.as_view(), name="zei-export"),
]
