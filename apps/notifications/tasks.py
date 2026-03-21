import logging

from celery import shared_task
from django.db import transaction

from apps.accounts.models import UserDevice
from apps.core.firebase import send_push
from .models import Notification, NotificationType

logger = logging.getLogger(__name__)


def _get_active_tokens(user_ids: list[int]) -> dict[int, list[str]]:
    """user_id → [fcm_token, ...] mapping qaytaradi."""
    devices = UserDevice.objects.filter(
        user_id__in=user_ids, is_active=True
    ).values("user_id", "fcm_token")

    result: dict[int, list[str]] = {}
    for d in devices:
        result.setdefault(d["user_id"], []).append(d["fcm_token"])
    return result


def _deactivate_invalid_tokens(invalid_tokens: list[str]):
    if invalid_tokens:
        UserDevice.objects.filter(fcm_token__in=invalid_tokens).update(is_active=False)


@transaction.atomic
def _bulk_create_notifications(user_ids: list[int], title: str, body: str,
                                notification_type: str, extra_data: dict):
    Notification.objects.bulk_create([
        Notification(
            user_id=uid,
            title=title,
            body=body,
            notification_type=notification_type,
            extra_data=extra_data,
        )
        for uid in user_ids
    ])


@shared_task(name="notifications.send_choice_started")
def send_choice_started(choice_id: int, choice_name: str, owner_id: int):
    """
    Tanlov yaratilganda owner ga notification yuboradi.
    """
    title = "Tanlov yaratildi!"
    body = f"'{choice_name}' nomli tanlov muvaffaqiyatli yaratildi."
    extra = {"choice_id": choice_id, "type": NotificationType.CHOICE_STARTED}

    _bulk_create_notifications([owner_id], title, body, NotificationType.CHOICE_STARTED, extra)

    tokens_map = _get_active_tokens([owner_id])
    tokens = tokens_map.get(owner_id, [])
    if tokens:
        result = send_push(title=title, body=body, tokens=tokens, data=extra)
        _deactivate_invalid_tokens(result["invalid_tokens"])
        logger.info("choice_started push: %s", result)


@shared_task(name="notifications.send_choice_ended")
def send_choice_ended(choice_id: int, choice_name: str, winner_id: int | None,
                      member_ids: list[int], award: int):
    """
    Tanlov tugaganda barcha a'zolarga + ownerlarga notification yuboradi.
    G'olibga alohida xabar yuboriladi.
    """
    all_ids = list(set(member_ids))
    if not all_ids:
        return

    # Barcha a'zolarga umumiy notification
    general_title = "Tanlov tugadi!"
    general_body = f"'{choice_name}' tanlov yakunlandi."
    general_extra = {"choice_id": choice_id, "type": NotificationType.CHOICE_ENDED}

    _bulk_create_notifications(all_ids, general_title, general_body,
                                NotificationType.CHOICE_ENDED, general_extra)

    tokens_map = _get_active_tokens(all_ids)

    # Barcha a'zolarga push
    for uid in all_ids:
        tokens = tokens_map.get(uid, [])
        if not tokens:
            continue

        if uid == winner_id:
            title = "Tabriklaymiz! 🏆"
            body = f"'{choice_name}' tanlovida g'olib bo'ldingiz! {award} coin hisobingizga o'tkazildi."
        else:
            title = general_title
            body = general_body

        if tokens:
            result = send_push(title=title, body=body, tokens=tokens, data=general_extra)
            _deactivate_invalid_tokens(result["invalid_tokens"])

    logger.info("choice_ended push yuborildi: %s ta a'zo", len(all_ids))
