import logging
import uuid

from django.db import transaction
from django.db.models import Count, Min, Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import CustomUser, UserDevice
from apps.news.models import Answer, Feedback
from apps.notifications.models import Notification, NotificationType
from ..mixins import AdminAPIMixin
from ..serializers import (
    AdminFeedbackSerializer, AdminNotificationSerializer, BroadcastSerializer,
    FeedbackAnswerSerializer,
)

logger = logging.getLogger(__name__)


class FeedbackViewSet(
    AdminAPIMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AdminFeedbackSerializer
    filterset_fields = ("status", "feedback_type", "owner")
    search_fields = ("subject", "message", "owner__phone", "owner__first_name")
    ordering_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        return Feedback.objects.select_related("owner").prefetch_related("answers")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        rows = Feedback.objects.values("status").annotate(c=Count("id"))
        data = {Feedback.NEW: 0, Feedback.IN_PROGRESS: 0, Feedback.RESOLVED: 0}
        data.update({row["status"]: row["c"] for row in rows})
        data["total"] = sum(data.values())
        return Response(data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def answer(self, request, pk=None):
        feedback = self.get_object()
        serializer = FeedbackAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Answer.objects.create(question=feedback, answer=serializer.validated_data["answer"])
        feedback.status = serializer.validated_data.get("status", Feedback.RESOLVED)
        feedback.save(update_fields=["status", "updated_at"])
        feedback = self.get_queryset().get(pk=feedback.pk)
        return Response(self.get_serializer(feedback).data, status=201)

    @action(detail=True, methods=["delete"], url_path=r"answers/(?P<answer_id>\d+)")
    def delete_answer(self, request, pk=None, answer_id=None):
        deleted, _ = Answer.objects.filter(question_id=pk, pk=answer_id).delete()
        if not deleted:
            return Response({"detail": "Javob topilmadi."}, status=404)
        return Response(status=204)


class NotificationViewSet(
    AdminAPIMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = AdminNotificationSerializer
    filterset_fields = ("notification_type", "is_read", "user")
    search_fields = ("title", "body", "user__phone")
    ordering_fields = ("id", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return Notification.objects.select_related("user")

    @action(detail=False, methods=["get"])
    def broadcasts(self, request):
        """Admin paneldan yuborilgan ommaviy xabarlar (broadcast_id bo'yicha guruhlangan)."""
        rows = (
            Notification.objects.filter(extra_data__has_key="broadcast_id")
            .values("extra_data__broadcast_id", "title", "body")
            .annotate(
                recipients=Count("id"),
                read=Count("id", filter=Q(is_read=True)),
                created_at=Min("created_at"),
            )
            .order_by("-created_at")[:100]
        )
        return Response([
            {
                "broadcast_id": row["extra_data__broadcast_id"],
                "title": row["title"],
                "body": row["body"],
                "recipients": row["recipients"],
                "read": row["read"],
                "created_at": row["created_at"],
            }
            for row in rows
        ])

    @action(detail=False, methods=["delete"], url_path=r"broadcasts/(?P<broadcast_id>[0-9a-f-]{36})")
    def delete_broadcast(self, request, broadcast_id=None):
        deleted, _ = Notification.objects.filter(extra_data__broadcast_id=broadcast_id).delete()
        if not deleted:
            return Response({"detail": "Xabar topilmadi."}, status=404)
        return Response(status=204)

    @action(detail=False, methods=["post"])
    def broadcast(self, request):
        serializer = BroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        users = CustomUser.objects.filter(is_active=True)
        if data["audience"] == "users":
            users = users.filter(pk__in=data["user_ids"])
        user_ids = list(users.values_list("pk", flat=True))
        if not user_ids:
            return Response({"detail": "Qabul qiluvchilar topilmadi."}, status=400)

        broadcast_id = str(uuid.uuid4())
        extra = {"type": NotificationType.SYSTEM, "broadcast_id": broadcast_id}
        Notification.objects.bulk_create(
            [
                Notification(
                    user_id=uid,
                    title=data["title"],
                    body=data["body"],
                    notification_type=NotificationType.SYSTEM,
                    extra_data=extra,
                )
                for uid in user_ids
            ],
            batch_size=500,
        )

        push_queued = False
        if UserDevice.objects.filter(user_id__in=user_ids, is_active=True).exists():
            try:
                from ..tasks import send_broadcast_push
                send_broadcast_push.delay(user_ids, data["title"], data["body"], extra)
                push_queued = True
            except Exception:
                logger.exception("Broadcast push navbatga qo'yilmadi")

        return Response(
            {"broadcast_id": broadcast_id, "recipients": len(user_ids), "push_queued": push_queued},
            status=201,
        )
