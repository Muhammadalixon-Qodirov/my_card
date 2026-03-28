from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.wallet.models import CoinTransaction
from .models import Choice, ChoiceMember
from .serializers import (
    ChoiceCreateSerializer,
    ChoiceDetailSerializer,
    ChoiceMemberSerializer,
    JoinChoiceSerializer,
    LeaderboardEntrySerializer,
)
from .tasks import close_choice, _calculate_member_score
from .permissions import IsOwner



class ChoiceViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return ChoiceCreateSerializer
        return ChoiceDetailSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Choice.objects.none()
        return Choice.objects.select_related("owner", "winner").prefetch_related("members")

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        award = serializer.validated_data["award"]

        CoinTransaction.objects.create(
            user=user,
            amount=award,
            transaction_type=CoinTransaction.SPEND,
            description=f"Tanlov yaratish uchun award: {serializer.validated_data['name']}",
        )
        serializer.save(owner=user)

        # Notification (Celery orqali async)
        from apps.notifications.tasks import send_choice_started
        choice_name = serializer.validated_data["name"]
        send_choice_started.delay(
            choice_id=serializer.instance.pk,
            choice_name=choice_name,
            owner_id=user.pk,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        choice = Choice.objects.select_related("owner", "winner").get(pk=serializer.instance.pk)
        return Response(ChoiceDetailSerializer(choice, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="join")
    def join(self, request):
        serializer = JoinChoiceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        choice = serializer.context["choice"]

        if ChoiceMember.objects.filter(choice=choice, user=request.user).exists():
            return Response(
                {"detail": "Siz allaqachon bu tanlovdasiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member = ChoiceMember.objects.create(choice=choice, user=request.user)
        return Response(ChoiceMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="leaderboard")
    def leaderboard(self, request, pk=None):
        choice = self.get_object()
        members = choice.members.select_related("user").all()
        results = []

        if choice.is_active:
            today = timezone.localdate()
            upper = min(choice.ended_at, today) if choice.ended_at else today

            for member in members:
                score = _calculate_member_score(member, choice.started_at, upper)
                results.append({
                    "user_id": member.user.pk,
                    "user_name": member.user.first_name,
                    "user_phone": member.user.phone,
                    "total_score": score,
                })
        else:
            for member in members:
                results.append({
                    "user_id": member.user.pk,
                    "user_name": member.user.first_name,
                    "user_phone": member.user.phone,
                    "total_score": member.final_score,
                })

        results.sort(key=lambda x: x["total_score"], reverse=True)
        for i, entry in enumerate(results, start=1):
            entry["rank"] = i

        return Response(LeaderboardEntrySerializer(results, many=True).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="finish",
        permission_classes=[permissions.IsAuthenticated, IsOwner],
    )
    def finish(self, request, pk=None):
        choice = self.get_object()

        if not choice.is_active:
            return Response(
                {"detail": "Bu tanlov allaqachon yakunlangan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not choice.members.exists():
            return Response(
                {"detail": "Tanlovda hech qanday a'zo yo'q."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        close_choice(choice)
        choice.refresh_from_db()

        response_data = {
            "detail": "Tanlov yakunlandi.",
        }
        if choice.winner:
            member = choice.members.filter(user=choice.winner).first()
            response_data["winner"] = {
                "user_id": choice.winner.pk,
                "user_name": choice.winner.first_name,
                "user_phone": choice.winner.phone,
                "total_score": member.final_score if member else 0,
                "coins_awarded": choice.award,
            }

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        choice = self.get_object()
        members = choice.members.select_related("user").all()
        return Response(ChoiceMemberSerializer(members, many=True).data)
