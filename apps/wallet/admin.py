from django.contrib import admin

from .models import CoinTransaction


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "transaction_type", "description", "module", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("user__phone", "description")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
