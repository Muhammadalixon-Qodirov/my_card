from django.contrib import admin
from django.utils.html import format_html

from .models import EmergencyNotification, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user_phone", "title", "notification_type", "is_read_badge", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("user__phone", "title", "body")
    readonly_fields = ("created_at",)
    list_per_page = 30
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("user",)
    actions = ("mark_as_read", "mark_as_unread")

    fieldsets = (
        ("Asosiy ma'lumot", {
            "fields": ("user", "title", "body", "notification_type"),
        }),
        ("Qo'shimcha", {
            "fields": ("extra_data", "is_read", "created_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Telefon", ordering="user__phone")
    def user_phone(self, obj):
        return obj.user.phone

    @admin.display(description="O'qilgan", boolean=False, ordering="is_read")
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color:green;">&#10003; O\'qilgan</span>')
        return format_html('<span style="color:red;">&#10007; Yangi</span>')

    @admin.action(description="Tanlanganlarni o'qilgan deb belgilash")
    def mark_as_read(self, request, queryset):
        updated = queryset.filter(is_read=False).update(is_read=True)
        self.message_user(request, f"{updated} ta bildirishnoma o'qilgan deb belgilandi.")

    @admin.action(description="Tanlanganlarni o'qilmagan deb belgilash")
    def mark_as_unread(self, request, queryset):
        updated = queryset.filter(is_read=True).update(is_read=False)
        self.message_user(request, f"{updated} ta bildirishnoma o'qilmagan deb belgilandi.")


@admin.register(EmergencyNotification)
class EmergencyNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "short_body", "created_at")
    search_fields = ("title", "body")
    readonly_fields = ("created_at",)
    list_per_page = 20
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    fieldsets = (
        ("Asosiy ma'lumot", {
            "fields": ("title", "body"),
        }),
        ("Meta", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Matn (qisqa)")
    def short_body(self, obj):
        return obj.body[:80] + "..." if len(obj.body) > 80 else obj.body
