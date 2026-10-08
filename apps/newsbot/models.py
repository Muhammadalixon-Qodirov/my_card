from django.db import models

from apps.news.models import News


class CollectedItem(models.Model):
    NEW = "new"
    SKIPPED = "skipped"
    REJECTED = "rejected"
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    FAILED = "failed"

    STATUS_CHOICES = (
        (NEW, "Yangi"),
        (SKIPPED, "O'tkazib yuborilgan"),
        (REJECTED, "AI rad etgan"),
        (PENDING, "Tasdiq kutilmoqda"),
        (APPROVED, "Tasdiqlangan"),
        (DECLINED, "Admin rad etgan"),
        (FAILED, "Xato"),
    )

    source = models.CharField(max_length=64, db_index=True)
    url = models.URLField(max_length=1000, unique=True)
    title = models.CharField(max_length=500, blank=True)
    text = models.TextField(blank=True)
    published_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEW, db_index=True)
    ai_reason = models.CharField(max_length=500, blank=True)
    draft_title = models.CharField(max_length=255, blank=True)
    draft_content = models.TextField(blank=True)
    telegram_messages = models.JSONField(default=list, blank=True)
    reviewed_by = models.CharField(max_length=255, blank=True)
    news = models.ForeignKey(News, related_name="collected_items", on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source}: {self.title[:60] or self.url}"
