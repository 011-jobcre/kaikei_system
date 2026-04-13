# =========================================================
# Core Project URLs
# =========================================================

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from common import views as common_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("account.urls")),
    path("", RedirectView.as_view(url="/accounts/dashboard/", permanent=False)),
    path("master/", include("master.urls")),
    path("journal/", include("journal.urls")),
    path("ledger/", include("ledger.urls")),
    path("report/", include("report.urls")),
    # HTMX helper to fetch flash messages partial
    path("_messages/", common_views.messages_partial, name="messages-partial"),
]
