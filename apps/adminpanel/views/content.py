from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.news.models import News, NewsLog, NewsMedia, Question
from apps.notifications.models import EmergencyNotification
from ..mixins import AdminAPIMixin, ReadAfterWriteMixin
from ..querysets import sub_count
from ..serializers import AdminEmergencySerializer, AdminFAQSerializer, AdminNewsSerializer


class NewsViewSet(AdminAPIMixin, ReadAfterWriteMixin, viewsets.ModelViewSet):
    serializer_class = AdminNewsSerializer
    search_fields = ("title", "content")
    ordering_fields = ("id", "created_at", "views_count", "title")
    ordering = ("-created_at",)

    def get_queryset(self):
        return News.objects.prefetch_related("media").annotate(
            views_count=sub_count(NewsLog.objects.filter(is_read=True), "news", distinct="user")
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["delete"], url_path=r"media/(?P<media_id>\d+)")
    def delete_media(self, request, pk=None, media_id=None):
        deleted, _ = NewsMedia.objects.filter(news_id=pk, pk=media_id).delete()
        if not deleted:
            return Response({"detail": "Media topilmadi."}, status=404)
        return Response(status=204)


class FAQViewSet(AdminAPIMixin, ReadAfterWriteMixin, viewsets.ModelViewSet):
    serializer_class = AdminFAQSerializer
    search_fields = ("question", "answer")
    ordering_fields = ("id", "created_at", "likes_count")
    ordering = ("created_at", "id")

    def get_queryset(self):
        return Question.objects.annotate(likes_count=Count("likes", distinct=True))


class EmergencyViewSet(AdminAPIMixin, viewsets.ModelViewSet):
    serializer_class = AdminEmergencySerializer
    filterset_fields = ("is_active",)
    search_fields = ("title", "body")
    ordering_fields = ("id", "created_at", "is_active")
    ordering = ("-created_at",)
    queryset = EmergencyNotification.objects.all()
