from django.contrib import admin

from .models import News, NewsMedia, NewsLog, Feedback, Answer, Question, QuestionLike


class NewsMediaInline(admin.TabularInline):
    model = NewsMedia
    extra = 1
    fields = ("media_file", "media_type")


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "content", "owner__phone")
    readonly_fields = ("created_at",)
    inlines = (NewsMediaInline,)


@admin.register(NewsMedia)
class NewsMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "news", "media_type", "created_at")
    list_filter = ("media_type", "created_at")
    search_fields = ("news__title",)
    readonly_fields = ("created_at",)


@admin.register(NewsLog)
class NewsLogAdmin(admin.ModelAdmin):
    list_display = ("id", "news", "user", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("news__title", "user__phone")
    readonly_fields = ("created_at",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "feedback_type", "subject", "status", "owner", "created_at")
    list_filter = ("feedback_type", "status", "created_at")
    search_fields = ("subject", "message", "owner__phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "created_at")
    list_filter = ("created_at",)
    search_fields = ("question__subject", "answer")
    readonly_fields = ("created_at",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "created_at")
    list_filter = ("created_at",)
    search_fields = ("question", "answer")
    readonly_fields = ("created_at",)


@admin.register(QuestionLike)
class QuestionLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("question__question", "user__phone")
    readonly_fields = ("created_at",)

