from rest_framework import permissions, viewsets, status
from rest_framework.response import Response
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from .models import News, NewsMedia, NewsLog, Feedback, Answer
from .serializers import NewsSerializer, NewsLogSerializer, FeedbackSerializer, AnswerSerializer
from apps.education.permissions import IsSuperUserForWrite


class NewsViewSet(viewsets.ModelViewSet):
    serializer_class = NewsSerializer
    permission_classes = (IsSuperUserForWrite,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return News.objects.none()

        views_count_subquery = (
            NewsLog.objects.filter(
                news_id=OuterRef("pk"),
                is_read=True,
            )
            .values("news_id")
            .annotate(count=Count("user_id", distinct=True))
            .values("count")[:1]
        )
        return (
            News.objects.select_related("owner")
            .prefetch_related("media")
            .annotate(
                views_count=Coalesce(
                    Subquery(views_count_subquery, output_field=IntegerField()),
                    Value(0),
                )
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        news = serializer.save(owner=self.request.user)
        self._handle_media(news)

    def perform_update(self, serializer):
        news = serializer.save()
        self._handle_media(news)

    def _handle_media(self, news):
        media_files = self.request.FILES.getlist("media_files")
        media_types = self.request.data.getlist("media_types")

        media_objects = []
        for i, media_file in enumerate(media_files):
            media_type = media_types[i] if i < len(media_types) else "image"
            if media_type not in ("image", "video"):
                continue
            media_objects.append(
                NewsMedia(news=news, media_file=media_file, media_type=media_type)
            )

        if media_objects:
            NewsMedia.objects.bulk_create(media_objects)


class NewsLogViewSet(viewsets.ModelViewSet):
    serializer_class = NewsLogSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return NewsLog.objects.none()

        qs = NewsLog.objects.select_related("news", "user").filter(user=self.request.user).order_by("-created_at")

        news_id = self.request.query_params.get("news")
        if news_id:
            qs = qs.filter(news_id=news_id)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        news = serializer.validated_data["news"]
        is_read = serializer.validated_data.get("is_read", False)

        log, created = NewsLog.objects.get_or_create(
            news=news,
            user=request.user,
            defaults={"is_read": is_read},
        )
        if not created and log.is_read != is_read:
            log.is_read = is_read
            log.save(update_fields=["is_read"])

        out_serializer = self.get_serializer(log)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(out_serializer.data, status=status_code)


class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Feedback.objects.none()
        if self.request.user.is_superuser:
            return Feedback.objects.select_related("owner").all()
        return Feedback.objects.select_related("owner").filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return (permissions.IsAdminUser(),)
        return super().get_permissions()


class AnswerViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerSerializer
    permission_classes = (IsSuperUserForWrite,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Answer.objects.none()
        return Answer.objects.select_related("question").all()
