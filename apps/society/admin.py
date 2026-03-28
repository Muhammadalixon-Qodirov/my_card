from django.contrib import admin

from .models import Choice, ChoiceMember


class ChoiceMemberInline(admin.TabularInline):
    model = ChoiceMember
    extra = 0
    fields = ("user", "final_score", "joined_at")
    readonly_fields = ("joined_at",)


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_public", "code", "owner", "winner", "award", "is_active", "started_at", "ended_at")
    list_filter = ("is_public", "is_active", "started_at")
    search_fields = ("name", "code", "owner__phone", "winner__phone")
    readonly_fields = ("code", "started_at")
    inlines = (ChoiceMemberInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("owner", "winner")


@admin.register(ChoiceMember)
class ChoiceMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "choice", "user", "final_score", "joined_at")
    list_filter = ("choice",)
    search_fields = ("choice__name", "user__phone")
    readonly_fields = ("joined_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("choice", "user")
