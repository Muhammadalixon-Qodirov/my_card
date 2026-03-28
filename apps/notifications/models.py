from django.db import models

from apps.accounts.models import CustomUser


class NotificationType(models.TextChoices):
    CHOICE_STARTED = "choice_started", "Tanlov boshlandi"
    CHOICE_ENDED = "choice_ended", "Tanlov tugadi"
    SYSTEM = "system", "Tizim"


class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    extra_data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ["-created_at"]

    def __str__(self):
        status = "o'qilgan" if self.is_read else "yangi"
        return f"{self.user.phone} | {self.get_notification_type_display()} | {status}"


class EmergencyNotification(models.Model):
    image = models.ImageField(upload_to="emergency_notifications/", null=True, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favqulodda bildirishnoma"
        verbose_name_plural = "Favqulodda bildirishnomalar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Favqulodda: {self.title}"
