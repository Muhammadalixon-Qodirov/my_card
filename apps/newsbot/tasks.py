import logging

from celery import shared_task
from django.core.cache import cache

from . import pipeline

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


@shared_task(name="newsbot.collect")
def collect():
    """Yangiliklar saytlarining feed'i bir necha soatnigina qamraydi, shuning uchun tez-tez o'qiladi."""
    return _locked(pipeline.collect)


@shared_task(name="newsbot.run")
def run():
    return _locked(pipeline.run)
