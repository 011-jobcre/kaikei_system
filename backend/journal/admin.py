# =========================================================
# Journal Admin
# =========================================================

from django.contrib import admin
from .models import ShiwakeDenpyo, ShiwakeMeisai


class ShiwakeMeisaiInline(admin.TabularInline):
    model = ShiwakeMeisai
    extra = 2
    fields = ["kari_kashi", "kamoku", "hojo", "bumon", "torihikisaki", "kingaku", "zei_kubun", "tekyou"]


@admin.register(ShiwakeDenpyo)
class ShiwakeDenpyoAdmin(admin.ModelAdmin):
    fields = ("denpyo_no", "date", "memo", "created_by", "is_locked")
    list_display = ["denpyo_no", "date", "memo", "created_by", "is_locked"]

    list_filter = ["date", "is_locked"]
    search_fields = ["denpyo_no", "memo"]
    readonly_fields = ["denpyo_no", "created_by"]
    inlines = [ShiwakeMeisaiInline]
    ordering = ["-date", "-denpyo_no"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
