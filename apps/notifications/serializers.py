from rest_framework import serializers

from .models import EmergencyNotification, Notification


class EmergencyNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyNotification
        fields = ("id", "title", "body", "image", "created_at")
        read_only_fields = ("id", "created_at")


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source="get_notification_type_display", read_only=True
    )

    class Meta:
        model = Notification
        fields = (
            "id", "title", "body",
            "notification_type", "notification_type_display",
            "extra_data", "is_read", "created_at",
        )
        read_only_fields = (
            "id", "title", "body", "notification_type",
            "notification_type_display", "extra_data", "created_at",
        )
