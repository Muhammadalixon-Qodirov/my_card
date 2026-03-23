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
