from rest_framework import serializers

from apps.wallet.models import CoinTransaction
from .models import Choice, ChoiceMember


class ChoiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "name", "description", "award", "ended_at")

    def validate_award(self, value):
        if value <= 0:
            raise serializers.ValidationError("Award kamida 1 coin bo'lishi kerak.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        balance = CoinTransaction.get_balance(request.user)
        award = attrs.get("award", 0)
        if balance < award:
            raise serializers.ValidationError(
                f"Yetarli coin yo'q. Sizning balansingiz: {balance} coin, kerakli: {award} coin."
            )
        return attrs


class ChoiceDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.first_name", read_only=True)
    owner_phone = serializers.CharField(source="owner.phone", read_only=True)
    winner_name = serializers.CharField(source="winner.first_name", read_only=True, default=None)
    winner_phone = serializers.CharField(source="winner.phone", read_only=True, default=None)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Choice
        fields = (
            "id", "name", "description", "code", "owner_name", "owner_phone",
            "winner_name", "winner_phone",
            "award", "is_active", "started_at", "ended_at", "member_count",
        )

    def get_member_count(self, obj):
        return obj.members.count()


class ChoiceMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.first_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = ChoiceMember
        fields = ("id", "user_name", "user_phone", "joined_at", "final_score")


class JoinChoiceSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8)

    def validate_code(self, value):
        try:
            choice = Choice.objects.get(code=value.upper(), is_active=True)
        except Choice.DoesNotExist:
            raise serializers.ValidationError("Bunday kod bilan faol tanlov topilmadi.")
        self.context["choice"] = choice
        return value.upper()


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    user_phone = serializers.CharField()
    total_score = serializers.IntegerField()
