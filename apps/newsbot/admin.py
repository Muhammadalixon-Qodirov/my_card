from django.contrib import admin

from .models import CollectedItem


@admin.register(CollectedItem)
class CollectedItemAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "title", "status", "published_at", "created_at")
    list_filter = ("status", "source", "created_at")
    search_fields = ("title", "draft_title", "url")
    readonly_fields = ("url", "telegram_messages", "news", "created_at", "updated_at")
    actions = ("retry",)

    @admin.action(description="Qayta ishlashga qaytarish")
    def retry(self, request, queryset):
        queryset.exclude(status=CollectedItem.APPROVED).update(
            status=CollectedItem.NEW, draft_title="", draft_content="", ai_reason="",
        )
