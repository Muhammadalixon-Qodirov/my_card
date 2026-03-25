from django.contrib import admin

from .models import (
	Category,
	Module,
	DataCard,
	DataCardMedia,
	ModuleLog,
	DataCardLog,
	Test,
	TestOption,
	TestAnswer,
	Score,
)


class DataCardMediaInline(admin.TabularInline):
	model = DataCardMedia
	extra = 1


class TestOptionInline(admin.TabularInline):
	model = TestOption
	extra = 2


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "owner", "created_at")
	list_filter = ("created_at",)
	search_fields = ("name", "description", "owner__phone")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "category", "owner", "created_at")
	list_filter = ("category", "created_at")
	search_fields = ("name", "description", "category__name", "owner__phone")

@admin.register(DataCard)
class DataCardAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "module", "owner", "created_at")
	list_filter = ("module", "created_at")
	search_fields = ("name", "description", "module__name", "owner__phone")
	inlines = (DataCardMediaInline,)


@admin.register(ModuleLog)
class ModuleLogAdmin(admin.ModelAdmin):
	list_display = ("id", "module", "user", "is_completed", "timestamp")
	list_filter = ("is_completed", "timestamp", "module")
	search_fields = ("module__name", "user__phone")


@admin.register(DataCardLog)
class DataCardLogAdmin(admin.ModelAdmin):
	list_display = ("id", "data_card", "user", "is_completed", "timestamp")
	list_filter = ("is_completed", "timestamp", "data_card")
	search_fields = ("data_card__name", "user__phone")


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
	list_display = ("id", "question", "module", "owner", "is_active", "created_at")
	list_filter = ("is_active", "module", "created_at")
	search_fields = ("question", "module__name", "owner__phone")
	inlines = (TestOptionInline,)


@admin.register(TestAnswer)
class TestAnswerAdmin(admin.ModelAdmin):
	list_display = ("id", "test", "user", "selected_option", "is_correct", "timestamp")
	list_filter = ("is_correct", "timestamp", "test")
	search_fields = ("test__question", "user__phone", "selected_option__option")


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "module", "score", "created_at", "updated_at")
	list_filter = ("module", "created_at")
	search_fields = ("user__phone", "module__name")
	readonly_fields = ("created_at", "updated_at")
	ordering = ("-updated_at",)
