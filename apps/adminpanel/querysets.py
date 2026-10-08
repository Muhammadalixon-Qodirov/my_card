from django.db.models import (
    Count, DateTimeField, F, IntegerField, OuterRef, Subquery, Sum, Value,
)
from django.db.models.functions import Coalesce, Greatest

from apps.accounts.models import CustomUser
from apps.education.models import (
    DataCard, DataCardLog, Module, ModuleComment, ModuleFeedback,
    ModuleLog, ModuleQuestion, Score, Test, TestAnswer,
)
from apps.wallet.models import CoinTransaction


def sub_count(queryset, ref, distinct=None):
    """OuterRef("pk") ga bog'langan qatorlar sonini subquery orqali hisoblaydi."""
    agg = Count(distinct, distinct=True) if distinct else Count("pk")
    sq = (
        queryset.filter(**{ref: OuterRef("pk")})
        .order_by()
        .values(ref)
        .annotate(c=agg)
        .values("c")[:1]
    )
    return Coalesce(Subquery(sq, output_field=IntegerField()), Value(0))


def sub_sum(queryset, ref, field):
    sq = (
        queryset.filter(**{ref: OuterRef("pk")})
        .order_by()
        .values(ref)
        .annotate(t=Sum(field))
        .values("t")[:1]
    )
    return Coalesce(Subquery(sq, output_field=IntegerField()), Value(0))


def _latest(queryset, ref, field):
    sq = queryset.filter(**{ref: OuterRef("pk")}).order_by(f"-{field}").values(field)[:1]
    return Coalesce(Subquery(sq, output_field=DateTimeField()), F("created_at"))


def users_queryset():
    return CustomUser.objects.annotate(
        total_score=sub_sum(Score.objects.all(), "user", "score"),
        coins_earned=sub_sum(
            CoinTransaction.objects.filter(transaction_type=CoinTransaction.EARN), "user", "amount"
        ),
        coins_spent=sub_sum(
            CoinTransaction.objects.filter(transaction_type=CoinTransaction.SPEND), "user", "amount"
        ),
        completed_modules=sub_count(
            ModuleLog.objects.filter(is_completed=True), "user", distinct="module"
        ),
    ).annotate(
        coin_balance=F("coins_earned") - F("coins_spent"),
        last_activity=Greatest(
            _latest(TestAnswer.objects.all(), "user", "timestamp"),
            _latest(DataCardLog.objects.all(), "user", "timestamp"),
            _latest(ModuleLog.objects.all(), "user", "timestamp"),
            Coalesce(F("last_login"), F("created_at")),
        ),
    )


def modules_queryset():
    return Module.objects.select_related("category").annotate(
        data_cards_count=sub_count(DataCard.objects.all(), "module"),
        tests_count=sub_count(Test.objects.filter(is_special=False), "module"),
        special_tests_count=sub_count(Test.objects.filter(is_special=True), "module"),
        questions_count=sub_count(ModuleQuestion.objects.all(), "module"),
        comments_count=sub_count(ModuleComment.objects.filter(reply_to__isnull=True), "module"),
        users_completed=sub_count(ModuleLog.objects.filter(is_completed=True), "module", distinct="user"),
        users_started=sub_count(ModuleLog.objects.all(), "module", distinct="user"),
        likes=sub_count(ModuleFeedback.objects.filter(reaction="like"), "module"),
        dislikes=sub_count(ModuleFeedback.objects.filter(reaction="dislike"), "module"),
    )
