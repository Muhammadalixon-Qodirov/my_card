import logging

from celery import shared_task
from django.core.cache import cache

from . import pipeline, telegram

logger = logging.getLogger(__name__)

LOCK_KEY = "newsbot:run-lock"
LOCK_TTL = 60 * 60


def _locked(job):
    if not cache.add(LOCK_KEY, 1, LOCK_TTL):
        logger.info("newsbot: oldingi ishga tushirish hali tugamagan")
        return None
    try:
        stats = job()
    finally:
        cache.delete(LOCK_KEY)
    logger.info("newsbot: %s", stats)
    return stats


def _summary(stats: dict | None) -> str:
    if stats is None:
        return "Oldingi ishga tushirish hali tugamagan, birozdan keyin urinib ko'ring."
    if stats["drafted"]:
        text = f"Tayyor: {stats['drafted']} ta qoralama yuborildi."
    else:
        text = "Mos yangi material topilmadi."
    text += f"\nYangi nomzodlar: {stats['new']}, AI tashladi: {stats['rejected']}, xato: {stats['failed']}."
    if stats["errors"]:
        text += f"\nO'qilmagan manbalar: {', '.join(stats['errors'])}."
    return text


@shared_task(name="newsbot.collect")
def collect():
    """Yangiliklar saytlarining feed'i bir necha soatnigina qamraydi, shuning uchun tez-tez o'qiladi."""
    return _locked(pipeline.collect)


@shared_task(name="newsbot.run")
def run(notify_chat_id: int | None = None):
    """notify_chat_id — /run yuborgan admin: natija nima bo'lsa ham unga javob yoziladi."""
    stats = _locked(pipeline.run)
    if notify_chat_id:
        try:
            telegram.api("sendMessage", chat_id=notify_chat_id, text=_summary(stats))
        except telegram.TelegramError as exc:
            logger.warning("newsbot: natija yuborilmadi: %s", exc)
    return stats
