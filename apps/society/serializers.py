from rest_framework import serializers

from apps.wallet.models import CoinTransaction
from .models import Choice, ChoiceMember


class ChoiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "name", "description", "award", "ended_at", "is_public")

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
    code = serializers.SerializerMethodField()
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
            "award", "is_public", "is_active", "started_at", "ended_at", "member_count",
        )

    def get_member_count(self, obj):
        return obj.members.count()

    def get_code(self, obj):
        if obj.is_public:
            return None

        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated and request.user.id == obj.owner_id:
            return obj.code

        return None


class ChoiceMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.first_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = ChoiceMember
        fields = ("id", "user_name", "user_phone", "joined_at", "final_score")


class JoinChoiceSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField(required=False)
    code = serializers.CharField(max_length=8, required=False, allow_blank=False)

    def validate(self, attrs):
        code = attrs.get("code")
        choice_id = attrs.get("choice_id")

        if code:
            try:
                choice = Choice.objects.get(code=code.upper(), is_active=True, is_public=False)
            except Choice.DoesNotExist:
                raise serializers.ValidationError({"code": "Bunday kod bilan faol private tanlov topilmadi."})

            attrs["code"] = code.upper()
            self.context["choice"] = choice
            return attrs

        if choice_id is None:
            raise serializers.ValidationError(
                {"detail": "Public tanlovga kirish uchun choice_id yuboring yoki private tanlov uchun code yuboring."}
            )

        try:
            choice = Choice.objects.get(id=choice_id, is_active=True)
        except Choice.DoesNotExist:
            raise serializers.ValidationError({"choice_id": "Bunday ID bilan faol tanlov topilmadi."})

        if not choice.is_public:
            raise serializers.ValidationError(
                {"detail": "Bu private tanlov. Kirish uchun code yuborish kerak."}
            )

        self.context["choice"] = choice
        return attrs


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    user_phone = serializers.CharField()
    total_score = serializers.IntegerField()
