from django.contrib import admin
from django.db.models import Sum, Q

from .models import CoinTransaction


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "transaction_type", "description", "module", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("user__phone", "description")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "module")
