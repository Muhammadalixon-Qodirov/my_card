from rest_framework import serializers

from .models import News, NewsMedia, NewsLog


ALLOWED_MEDIA_TYPES = ("image", "video")



class NewsMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsMedia
        fields = ("id", "media_file", "media_type", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_media_type(self, value):
        if value not in ALLOWED_MEDIA_TYPES:
            raise serializers.ValidationError(
                f"media_type must be one of: {', '.join(ALLOWED_MEDIA_TYPES)}."
            )
        return value


class NewsSerializer(serializers.ModelSerializer):
    media = NewsMediaSerializer(many=True, read_only=True)
    views_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = News
        fields = ("id", "title", "content", "owner", "media", "views_count", "created_at")
        read_only_fields = ("id", "owner", "created_at")


class NewsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsLog
        fields = ("id", "news", "user", "is_read", "created_at")
        read_only_fields = ("id", "user", "created_at")
