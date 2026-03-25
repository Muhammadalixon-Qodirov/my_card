from django.db import models

from apps.accounts.models import CustomUser


# Create your models here.
class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    owner = models.ForeignKey(CustomUser, related_name="news", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class NewsMedia(models.Model):
    news = models.ForeignKey(News, related_name="media", on_delete=models.CASCADE)
    media_file = models.FileField(upload_to="news_media/")
    media_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Media for {self.news.title}"


class NewsLog(models.Model):
    news = models.ForeignKey(News, related_name="logs", on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, related_name="news_logs", on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("news", "user")

    def __str__(self):
        return f"Log for {self.news.title} by {self.user.username}"


class Feedback(models.Model):
    COMPLAINT = "complaint"
    SUGGESTION = "suggestion"
    PROBLEM = "problem"

    TYPE_CHOICES = (
        (COMPLAINT, "Shikoyat"),
        (SUGGESTION, "Taklif"),
        (PROBLEM, "Muammo"),
    )

    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"

    STATUS_CHOICES = (
        (NEW, "Yangi"),
        (IN_PROGRESS, "Jarayonda"),
        (RESOLVED, "Hal qilingan"),
    )

    feedback_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEW)
    owner = models.ForeignKey(CustomUser, related_name="feedbacks", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.feedback_type}: {self.subject}"
