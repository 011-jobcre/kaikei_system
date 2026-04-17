# =========================================================
# Master Admin
# =========================================================

from django.contrib import admin
from .models import (
    KanjoKamokuMaster,
    HojoKamokuMaster,
    BumonMaster,
    ZeiMaster,
    TorihikiSakiMaster,
)


@admin.register(KanjoKamokuMaster)
class KanjoKamokuAdmin(admin.ModelAdmin):
    fields = ("code", "name", "parent", "is_active")
    list_display = ["code", "name", "level", "parent", "taisha_kubun", "is_active"]

    list_filter = ["level", "taisha_kubun", "is_active"]
    search_fields = ["code", "name"]
    ordering = ["code"]


@admin.register(HojoKamokuMaster)
class HojoKamokuAdmin(admin.ModelAdmin):
    fields = ("code", "name", "kamoku", "is_active")
    list_display = ["code", "name", "kamoku", "is_active"]

    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["kamoku__code", "code"]


@admin.register(BumonMaster)
class BumonAdmin(admin.ModelAdmin):
    fields = ("code", "name", "manager_name", "annual_budget", "is_active")
    list_display = ["code", "name", "manager_name", "annual_budget", "is_active"]

    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["code"]


@admin.register(ZeiMaster)
class ZeiAdmin(admin.ModelAdmin):
    fields = ("zei_name", "tax_rate", "valid_from", "valid_to", "is_active", "order_no")
    list_display = ["zei_name", "tax_rate", "valid_from", "valid_to", "is_active", "order_no"]

    list_filter = ["is_active"]
    search_fields = ["zei_name"]
    ordering = ["order_no"]


@admin.register(TorihikiSakiMaster)
class TorihikiSakiAdmin(admin.ModelAdmin):
    fields = ("code", "name", "address", "phone", "email", "is_active")
    list_display = ["code", "name", "address", "phone", "email", "is_active"]

    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["code"]
