from rest_framework import serializers

from .models import CoinTransaction


class CoinTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )

    class Meta:
        model = CoinTransaction
        fields = (
            "id",
            "user",
            "amount",
            "transaction_type",
            "transaction_type_display",
            "description",
            "module",
            "created_at",
        )
        read_only_fields = ("id", "user", "created_at")


class CoinBalanceSerializer(serializers.Serializer):
    balance = serializers.IntegerField(read_only=True)
