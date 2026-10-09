import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import pipeline, telegram
from .tasks import run

logger = logging.getLogger(__name__)


def _answer(callback: dict, text: str):
    # Telegram eskirgan so'rovga javobni rad etadi; qaror baribir qo'llanishi kerak.
    try:
        telegram.api("answerCallbackQuery", callback_query_id=callback["id"], text=text)
    except telegram.TelegramError as exc:
        logger.warning("newsbot: %s", exc)


def _handle_callback(callback: dict):
    user = callback.get("from", {})
    if user.get("id") not in settings.NEWSBOT_ADMIN_CHAT_IDS:
        _answer(callback, "Ruxsat yo'q")
        return

    try:
        prefix, action, item_id = callback.get("data", "").split(":")
        item_id = int(item_id)
    except ValueError:
        return
    if prefix != "nb" or action not in ("approve", "noimg", "decline"):
        return

    approved = action != "decline"
    reviewer = user.get("username") or user.get("first_name") or str(user["id"])
    item = pipeline.review(item_id, approve=approved, reviewer=reviewer, with_image=action == "approve")
    if item is None:
        _answer(callback, "Allaqachon ko'rib chiqilgan")
        return

    _answer(callback, "Ilovaga joylandi" if approved else "Rad etildi")
    footer = f"✅ Tasdiqladi: {reviewer}" if approved else f"❌ Rad etdi: {reviewer}"
    telegram.mark_reviewed(item, pipeline.source_name(item.source), footer)


def _handle_message(message: dict):
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if text.startswith("/start"):
        telegram.api("sendMessage", chat_id=chat_id, text=f"Sizning chat ID: {chat_id}")
    elif text.startswith("/run") and chat_id in settings.NEWSBOT_ADMIN_CHAT_IDS:
        run.delay()
        telegram.api("sendMessage", chat_id=chat_id, text="Yig'ish boshlandi, qoralamalar shu yerga keladi.")


@csrf_exempt
@require_POST
def telegram_webhook(request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not settings.NEWSBOT_WEBHOOK_SECRET or not hmac.compare_digest(secret, settings.NEWSBOT_WEBHOOK_SECRET):
        return HttpResponseForbidden()

    try:
        update = json.loads(request.body)
        if "callback_query" in update:
            _handle_callback(update["callback_query"])
        elif "message" in update:
            _handle_message(update["message"])
    except telegram.TelegramError as exc:
        logger.warning("newsbot webhook: %s", exc)
    except Exception:
        # Telegram 200 olmasa, shu update'ni qayta-qayta yuboradi.
        logger.exception("newsbot webhook xatosi")
    return HttpResponse("ok")
