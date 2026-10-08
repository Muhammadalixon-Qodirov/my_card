from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.society.models import Choice, ChoiceMember
from apps.society.tasks import _calculate_member_score, close_choice
from apps.wallet.models import CoinTransaction
from ..mixins import AdminAPIMixin
from ..querysets import sub_count
from ..serializers import (
    AdminChoiceMemberSerializer, AdminChoiceSerializer, AdminTransactionSerializer,
    UserBriefSerializer,
)


class TransactionViewSet(AdminAPIMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminTransactionSerializer
    filterset_fields = ("transaction_type", "user", "module")
    search_fields = ("description", "user__phone", "user__first_name")
    ordering_fields = ("id", "created_at", "amount")
    ordering = ("-created_at",)

    def get_queryset(self):
        return CoinTransaction.objects.select_related("user", "module")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        totals = CoinTransaction.objects.aggregate(
            earned=Sum("amount", filter=Q(transaction_type=CoinTransaction.EARN)),
            spent=Sum("amount", filter=Q(transaction_type=CoinTransaction.SPEND)),
        )
        earned = totals["earned"] or 0
        spent = totals["spent"] or 0
        return Response({
            "earned": earned,
            "spent": spent,
            "circulation": earned - spent,
            "transactions": CoinTransaction.objects.count(),
            "holders": CoinTransaction.objects.values("user").distinct().count(),
        })


class ChoiceViewSet(
    AdminAPIMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AdminChoiceSerializer
    filterset_fields = ("is_active", "is_public", "owner")
    search_fields = ("name", "description", "code", "owner__phone")
    ordering_fields = ("id", "started_at", "ended_at", "award", "member_count")
    ordering = ("-started_at", "-id")
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        return Choice.objects.select_related("owner", "winner").annotate(
            member_count=sub_count(ChoiceMember.objects.all(), "choice")
        )

    @action(detail=True, methods=["get"])
    def leaderboard(self, request, pk=None):
        choice = self.get_object()
        today = timezone.localdate()
        upper = min(choice.ended_at, today) if choice.ended_at else today
        rows = []
        for member in choice.members.select_related("user"):
            score = (
                _calculate_member_score(member, choice.started_at, upper)
                if choice.is_active else member.final_score
            )
            rows.append({
                "member_id": member.pk,
                "user": UserBriefSerializer(member.user, context={"request": request}).data,
                "joined_at": member.joined_at,
                "total_score": score,
            })
        rows.sort(key=lambda r: r["total_score"], reverse=True)
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
        return Response(rows)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        choice = self.get_object()
        if not choice.is_active:
            return Response({"detail": "Bu tanlov allaqachon yakunlangan."}, status=400)
        close_choice(choice)
        return Response(self.get_serializer(self.get_queryset().get(pk=choice.pk)).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        choice = self.get_object()
        refund = request.query_params.get("refund") in ("1", "true")
        if refund and choice.is_active and choice.award > 0:
            CoinTransaction.objects.create(
                user=choice.owner,
                amount=choice.award,
                transaction_type=CoinTransaction.EARN,
                description=f"'{choice.name}' tanlovi bekor qilindi: mukofot qaytarildi"[:255],
            )
        choice.delete()
        return Response(status=204)
