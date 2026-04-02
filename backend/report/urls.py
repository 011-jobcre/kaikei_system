from django.urls import path

from . import views

app_name = "report"

urlpatterns = [
    path("bs/", views.BalanceSheetView.as_view(), name="balance-sheet"),
    path("pl/", views.IncomeStatementView.as_view(), name="income-statement"),
]
