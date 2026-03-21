from django.db import models
from django.contrib.auth.models import AbstractUser

from .managers import UserManager
from apps.core.validators import validate_phone_number


class DeviceType(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"
    WEB = "web", "Web"


class CustomUser(AbstractUser):
    gender = (
        ('male', "Erkak"),
        ('female', "Ayol"),
    )
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    first_name = models.CharField(max_length=50, db_index=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=gender, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True, db_index=True, validators=[validate_phone_number])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    username = None
    email = None
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ['-created_at']

    def __str__(self):
        return self.phone


class UserDevice(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="devices")
    fcm_token = models.TextField(unique=True)
    device_type = models.CharField(max_length=10, choices=DeviceType.choices, default=DeviceType.ANDROID)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Qurilma"
        verbose_name_plural = "Qurilmalar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.phone} | {self.device_type} | {'faol' if self.is_active else 'nofaol'}"
