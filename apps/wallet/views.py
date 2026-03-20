from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CoinTransaction
from .serializers import CoinTransactionSerializer, CoinBalanceSerializer


class CoinTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Foydalanuvchining coin tranzaksiyalarini ko'rish va balansini olish.
    Yozish faqat tizim ichidan (education views) amalga oshiriladi.
    """
    serializer_class = CoinTransactionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CoinTransaction.objects.none()
        return CoinTransaction.objects.select_related("user", "module").filter(
            user=self.request.user
        )

    @action(detail=False, methods=["get"], url_path="balance")
    def balance(self, request):
        """Foydalanuvchining joriy coin balansini qaytaradi."""
        bal = CoinTransaction.get_balance(request.user)
        serializer = CoinBalanceSerializer({"balance": bal})
        return Response(serializer.data, status=status.HTTP_200_OK)
