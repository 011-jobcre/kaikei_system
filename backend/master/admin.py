from django.contrib import admin

from .models import BumonMaster, KanjoKamokuMaster, TorihikiSakiMaster, ZeiMaster


@admin.register(KanjoKamokuMaster)
class KanjoKamokuAdmin(admin.ModelAdmin):
    fields = ("code", "name", "parent", "is_active")
    list_display = ["code", "name", "level", "parent", "taisha_kubun", "is_active"]

    list_filter = ["level", "taisha_kubun", "is_active"]
    search_fields = ["code", "name"]
    ordering = ["code"]


@admin.register(BumonMaster)
class BumonAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "manager_name", "is_active"]
    search_fields = ["code", "name"]


@admin.register(ZeiMaster)
class ZeiAdmin(admin.ModelAdmin):
    list_display = ["zei_kubun", "zei_name", "tax_rate", "is_active"]
    ordering = ["order_no"]


@admin.register(TorihikiSakiMaster)
class TorihikiSakiAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "phone", "email", "is_active"]
    search_fields = ["code", "name"]
