from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, UserDevice


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("id", "phone", "first_name", "last_name", "gender", "is_active", "is_staff", "created_at")
    list_filter = ("is_active", "is_staff", "gender")
    search_fields = ("phone", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Shaxsiy ma'lumotlar", {"fields": ("first_name", "last_name", "gender", "birth_date", "profile_image")}),
        ("Huquqlar", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Sanalar", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "first_name", "password1", "password2", "is_staff", "is_active"),
        }),
    )


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "device_type", "is_active", "created_at")
    list_filter = ("device_type", "is_active")
    search_fields = ("user__phone",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

