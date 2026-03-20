from django.db import models
from django.db.models import Sum

from apps.accounts.models import CustomUser


class CoinTransaction(models.Model):
    EARN = "earn"
    SPEND = "spend"

    TRANSACTION_TYPES = [
        (EARN, "Ishlandi"),
        (SPEND, "Sarflandi"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="coin_transactions",
    )
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        db_index=True,
    )
    description = models.CharField(max_length=255, blank=True, null=True)
    module = models.ForeignKey(
        "education.Module",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coin_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Coin Transaction"
        verbose_name_plural = "Coin Transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.phone} | {self.get_transaction_type_display()} | {self.amount} coin"

    @staticmethod
    def get_balance(user) -> int:
        """Foydalanuvchining hozirgi coin balansini hisoblaydi."""
        result = CoinTransaction.objects.filter(user=user).aggregate(
            earned=Sum("amount", filter=models.Q(transaction_type=CoinTransaction.EARN)),
            spent=Sum("amount", filter=models.Q(transaction_type=CoinTransaction.SPEND)),
        )
        earned = result["earned"] or 0
        spent = result["spent"] or 0
        return earned - spent
