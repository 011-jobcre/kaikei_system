from django.contrib import admin

from .models import ShiwakeDenpyo, ShiwakeMeisai


class ShiwakeMeisaiInline(admin.TabularInline):
    model = ShiwakeMeisai
    extra = 2
    fields = ["kari_kashi", "kamoku", "bumon", "kingaku", "tekyou"]


@admin.register(ShiwakeDenpyo)
class ShiwakeDenpyoAdmin(admin.ModelAdmin):
    list_display = ["denpyo_no", "date", "memo", "created_by", "is_locked"]
    list_filter = ["is_locked", "date"]
    search_fields = ["denpyo_no", "memo"]
    readonly_fields = ["denpyo_no", "created_by"]
    inlines = [ShiwakeMeisaiInline]
    ordering = ["-date", "-denpyo_no"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
