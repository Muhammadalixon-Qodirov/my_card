import logging

from celery import shared_task

from apps.core.firebase import send_push
from apps.notifications.tasks import _deactivate_invalid_tokens, _get_active_tokens

logger = logging.getLogger(__name__)


@shared_task(name="adminpanel.send_broadcast_push")
def send_broadcast_push(user_ids: list[int], title: str, body: str, extra: dict):
    tokens = [t for user_tokens in _get_active_tokens(user_ids).values() for t in user_tokens]
    sent = 0
    for start in range(0, len(tokens), 400):
        result = send_push(title=title, body=body, tokens=tokens[start:start + 400], data=extra)
        _deactivate_invalid_tokens(result["invalid_tokens"])
        sent += result["success"]
    logger.info("broadcast push: %s / %s", sent, len(tokens))
    return sent
