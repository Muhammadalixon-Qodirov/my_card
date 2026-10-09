import html
import logging

import requests
from django.conf import settings

from .fetchers import download_image

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 3300


class TelegramError(Exception):
    pass


def api(method: str, files: dict | None = None, **payload) -> dict:
    if not settings.NEWSBOT_TELEGRAM_TOKEN:
        raise TelegramError("NEWSBOT_TELEGRAM_TOKEN sozlanmagan")
    body = {"data": payload, "files": files} if files else {"json": payload}
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{settings.NEWSBOT_TELEGRAM_TOKEN}/{method}",
            timeout=60, **body,
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise TelegramError(f"{method}: {type(exc).__name__}") from exc
    if not data.get("ok"):
        raise TelegramError(f"{method}: {data.get('description')}")
    return data["result"]


def draft_text(item, source_name: str, footer: str = "") -> str:
    content = item.draft_content
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + "…"
    text = (
        f"<b>{html.escape(item.draft_title)}</b>\n\n"
        f"{html.escape(content)}\n\n"
        f"Manba: <a href=\"{html.escape(item.url)}\">{html.escape(source_name)}</a>\n"
        f"Asl sarlavha: {html.escape(item.title[:200])}"
    )
    return f"{text}\n\n{footer}" if footer else text


def send_photo(chat_id: int, item):
    caption = item.draft_title[:200]
    try:
        api("sendPhoto", chat_id=chat_id, photo=item.image_url, caption=caption)
        return
    except TelegramError:
        pass
    # Ba'zi saytlar Telegram serverlariga rasm bermaydi: o'zimiz yuklab, fayl qilib yuboramiz.
    try:
        data, extension = download_image(item.image_url)
        api("sendPhoto", files={"photo": (f"image{extension}", data)}, chat_id=chat_id, caption=caption)
    except Exception as exc:
        logger.warning("newsbot: rasm ko'rsatilmadi %s: %s", item.image_url, exc)


def send_draft(item, source_name: str) -> list[list[int]]:
    """Qoralamani barcha adminlarga yuboradi, [[chat_id, message_id], ...] qaytaradi."""
    rows = [[
        {"text": "✅ Tasdiqlash", "callback_data": f"nb:approve:{item.pk}"},
        {"text": "❌ Rad etish", "callback_data": f"nb:decline:{item.pk}"},
    ]]
    if item.image_url:
        rows.append([{"text": "✅ Rasmsiz tasdiqlash", "callback_data": f"nb:noimg:{item.pk}"}])
    keyboard = {"inline_keyboard": rows}
    sent = []
    for chat_id in settings.NEWSBOT_ADMIN_CHAT_IDS:
        if item.image_url:
            send_photo(chat_id, item)
        try:
            message = api(
                "sendMessage", chat_id=chat_id, text=draft_text(item, source_name),
                parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard,
            )
            sent.append([chat_id, message["message_id"]])
        except TelegramError as exc:
            logger.error("newsbot: %s ga yuborilmadi: %s", chat_id, exc)
    if not sent:
        raise TelegramError("Qoralama hech kimga yuborilmadi")
    return sent


def mark_reviewed(item, source_name: str, footer: str):
    for chat_id, message_id in item.telegram_messages:
        try:
            api(
                "editMessageText", chat_id=chat_id, message_id=message_id,
                text=draft_text(item, source_name, footer),
                parse_mode="HTML", disable_web_page_preview=True,
            )
        except TelegramError as exc:
            logger.warning("newsbot: xabar yangilanmadi: %s", exc)
