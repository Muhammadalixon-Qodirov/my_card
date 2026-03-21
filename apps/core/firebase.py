import logging

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_app = None


def _get_app():
    global _app
    if _app is None:
        cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
        if not cred_path:
            raise RuntimeError("FIREBASE_CREDENTIALS_PATH settings da ko'rsatilmagan.")
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred)
    return _app


def send_push(*, title: str, body: str, tokens: list[str], data: dict | None = None) -> dict:
    """
    Bir yoki bir nechta FCM token ga push notification yuboradi.

    Returns:
        {"success": int, "failure": int, "invalid_tokens": list[str]}
    """
    if not tokens:
        return {"success": 0, "failure": 0, "invalid_tokens": []}

    _get_app()

    notification = messaging.Notification(title=title, body=body)
    messages = [
        messaging.Message(
            notification=notification,
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        for token in tokens
    ]

    batch_response = messaging.send_each(messages)

    invalid_tokens = []
    for idx, resp in enumerate(batch_response.responses):
        if not resp.success:
            err_code = resp.exception.code if resp.exception else "unknown"
            logger.warning("FCM xato token=%s code=%s", tokens[idx], err_code)
            # Eskirgan yoki notog'ri tokenlarni belgilash
            if err_code in (
                "registration-token-not-registered",
                "invalid-registration-token",
            ):
                invalid_tokens.append(tokens[idx])

    return {
        "success": batch_response.success_count,
        "failure": batch_response.failure_count,
        "invalid_tokens": invalid_tokens,
    }
