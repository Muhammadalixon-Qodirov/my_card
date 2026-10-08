from django.db import transaction
from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import CustomUser
from apps.accounts.serializers import UserProfileSerializer
from apps.education.models import DataCardLog, ModuleComment, TestAnswer
from apps.news.models import Feedback
from apps.society.models import Choice, ChoiceMember
from apps.wallet.models import CoinTransaction
from ..mixins import AdminAPIMixin, ReadAfterWriteMixin
from ..querysets import users_queryset
from ..serializers import (
    AdminUserSerializer, AdminUserWriteSerializer, CoinAdjustSerializer,
    SetPasswordSerializer, UserDeviceSerializer,
)

# Bu bog'lanishlar CASCADE — foydalanuvchi o'chsa, kontent ham o'chib ketadi.
OWNED_CONTENT = {
    "categories": "kategoriya",
    "modules": "modul",
    "data_cards": "datacard",
    "tests": "test",
    "news": "yangilik",
}


def owned_content_counts(user):
    return {name: getattr(user, name).count() for name in OWNED_CONTENT}


class UserViewSet(AdminAPIMixin, ReadAfterWriteMixin, viewsets.ModelViewSet):
    serializer_class = AdminUserSerializer
    write_serializer_class = AdminUserWriteSerializer
    filterset_fields = ("is_active", "is_staff", "is_superuser", "gender")
    search_fields = ("phone", "first_name", "last_name")
    ordering_fields = (
        "id", "created_at", "first_name", "phone", "last_login",
        "total_score", "coin_balance", "completed_modules", "last_activity",
    )
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = users_queryset()
        params = self.request.query_params
        if params.get("has_score") in ("1", "true"):
            qs = qs.filter(total_score__gt=0)
        if params.get("created_after"):
            qs = qs.filter(created_at__date__gte=params["created_after"])
        if params.get("created_before"):
            qs = qs.filter(created_at__date__lte=params["created_before"])
        return qs

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        data = AdminUserSerializer(user, context=self.get_serializer_context()).data
        answers = TestAnswer.objects.filter(user=user).aggregate(
            total=Count("id"), correct=Count("id", filter=Q(is_correct=True))
        )
        data["stats"] = {
            "learning_progress": UserProfileSerializer().get_learning_progress(user),
            "coins_earned": user.coins_earned,
            "coins_spent": user.coins_spent,
            "test_answers": answers["total"],
            "correct_answers": answers["correct"],
            "data_cards_completed": DataCardLog.objects.filter(user=user, is_completed=True)
            .values("data_card").distinct().count(),
            "feedbacks": Feedback.objects.filter(owner=user).count(),
            "comments": ModuleComment.objects.filter(user=user, is_admin_reply=False).count(),
            "choices_owned": Choice.objects.filter(owner=user).count(),
            "choices_joined": ChoiceMember.objects.filter(user=user).count(),
            "choices_won": Choice.objects.filter(winner=user).count(),
        }
        data["owned_content"] = owned_content_counts(user)
        data["devices"] = UserDeviceSerializer(user.devices.all(), many=True).data
        return Response(data)

    def _guard_self(self, request, instance, data):
        """Admin o'zini bloklab yoki huquqidan mahrum qilib qo'ymasligi uchun."""
        if instance.pk != request.user.pk:
            return None
        for field in ("is_active", "is_superuser", "is_staff"):
            if field in data and str(data.get(field)).lower() in ("false", "0"):
                return Response(
                    {"detail": "O'z hisobingizni bloklash yoki admin huquqini olib tashlash mumkin emas."},
                    status=400,
                )
        return None

    def update(self, request, *args, **kwargs):
        blocked = self._guard_self(request, self.get_object(), request.data)
        if blocked:
            return blocked
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({"detail": "O'z hisobingizni o'chira olmaysiz."}, status=400)
        owned = {k: v for k, v in owned_content_counts(user).items() if v}
        if owned:
            summary = ", ".join(f"{count} ta {OWNED_CONTENT[name]}" for name, count in owned.items())
            return Response(
                {
                    "detail": (
                        f"Bu foydalanuvchi kontent egasi ({summary}). O'chirilsa kontent ham o'chib ketadi. "
                        "Buning o'rniga hisobni bloklang."
                    ),
                    "owned_content": owned,
                },
                status=409,
            )
        user.delete()
        return Response(status=204)

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Parol yangilandi."})

    @action(detail=True, methods=["post"], url_path="coins")
    @transaction.atomic
    def coins(self, request, pk=None):
        user = self.get_object()
        serializer = CoinAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        balance = CoinTransaction.get_balance(user)
        if data["transaction_type"] == CoinTransaction.SPEND and data["amount"] > balance:
            return Response(
                {"detail": f"Balans yetarli emas. Joriy balans: {balance} coin."}, status=400
            )

        default = "Admin tomonidan qo'shildi" if data["transaction_type"] == CoinTransaction.EARN \
            else "Admin tomonidan yechildi"
        CoinTransaction.objects.create(
            user=user,
            amount=data["amount"],
            transaction_type=data["transaction_type"],
            description=(data.get("description") or default)[:255],
        )
        return Response({"balance": CoinTransaction.get_balance(user)})
