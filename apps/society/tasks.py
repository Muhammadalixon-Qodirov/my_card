import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Choice
from apps.education.models import ModuleLog
from apps.wallet.models import CoinTransaction

logger = logging.getLogger(__name__)


def _calculate_member_score(member, started_at, ended_at):
    qs = ModuleLog.objects.filter(
        user=member.user,
        is_completed=True,
        timestamp__date__gte=started_at,
    )
    if ended_at:
        qs = qs.filter(timestamp__date__lte=ended_at)
    return qs.aggregate(total=Sum("module__score"))["total"] or 0


@transaction.atomic
def close_choice(choice):
    members = list(choice.members.select_related("user").all())

    if not members:
        choice.is_active = False
        choice.save(update_fields=["is_active"])
        logger.info("Choice #%s '%s' — a'zo yo'q, yopildi.", choice.pk, choice.name)
        return

    ended_at = choice.ended_at or timezone.localdate()

    best_member = None
    best_score = -1

    for member in members:
        score = _calculate_member_score(member, choice.started_at, ended_at)
        member.final_score = score
        if score > best_score:
            best_score = score
            best_member = member

    from .models import ChoiceMember
    ChoiceMember.objects.bulk_update(members, ["final_score"])

    if best_member is not None:
        CoinTransaction.objects.create(
            user=best_member.user,
            amount=choice.award,
            transaction_type=CoinTransaction.EARN,
            description=f"'{choice.name}' tanlovida g'olib bo'lganlik uchun mukofot",
        )
        choice.winner = best_member.user
        logger.info(
            "Choice #%s '%s' — g'olib: %s (%s ball), %s coin berildi.",
            choice.pk, choice.name, best_member.user.phone, best_score, choice.award,
        )

    choice.is_active = False
    if not choice.ended_at:
        choice.ended_at = ended_at
    choice.save(update_fields=["is_active", "ended_at", "winner"])

    # Notification (Celery orqali async)
    from apps.notifications.tasks import send_choice_ended
    member_ids = [m.user_id for m in members]
    send_choice_ended.delay(
        choice_id=choice.pk,
        choice_name=choice.name,
        winner_id=best_member.user_id if best_member else None,
        member_ids=member_ids,
        award=choice.award,
    )


@shared_task(name="society.close_expired_choices")
def close_expired_choices():
    today = timezone.localdate()
    expired = Choice.objects.filter(is_active=True, ended_at__lte=today).select_related("owner")

    count = expired.count()
    if count == 0:
        logger.info("Muddati tugagan faol tanlov topilmadi.")
        return "no_expired"

    logger.info("%s ta muddati tugagan tanlov yopilmoqda...", count)

    closed = 0
    for choice in expired:
        try:
            close_choice(choice)
            closed += 1
        except Exception as exc:
            logger.exception("Choice #%s yopishda xato: %s", choice.pk, exc)

    logger.info("%s / %s tanlov muvaffaqiyatli yopildi.", closed, count)
    return f"closed:{closed}"
