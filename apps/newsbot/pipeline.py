import logging
import re
import time
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.news.models import News, NewsMedia
from . import llm, telegram
from .fetchers import download_image, fetch_article, fetch_source
from .models import CollectedItem
from .sources import SOURCES, SOURCES_BY_KEY

logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 500

# Umumiy manbalardan faqat shu so'zlar uchraganlari olinadi (o'zbek / rus / ingliz).
KEYWORDS = re.compile(
    r"firibgar|kiber|fishing|xaker|zararli\s+(dastur|ilova|havola|fayl)|sms.{0,3}kod|"
    r"akkaunt\w*\s+(o.g.ir|egalla|buz)|karta\w*\s+ma.lumot|"
    r"мошенн|кибер|фишинг|хакер|вредонос|взлом|утечк\w+\s+данных|скам|троян|"
    r"scam|phishing|fraud|malware|data\s+breach",
    re.I,
)
MIN_BODY_HITS = 2


def is_candidate(title: str, text: str) -> bool:
    """Sarlavhada kalit so'z bo'lsa yoki matnda kamida ikki xil kalit so'z uchrasa."""
    if KEYWORDS.search(title):
        return True
    hits = {match.group(0).lower()[:5] for match in KEYWORDS.finditer(text)}
    return len(hits) >= MIN_BODY_HITS


def source_name(key: str) -> str:
    source = SOURCES_BY_KEY.get(key)
    return source["name"] if source else key


def active_sources() -> list[dict]:
    return [s for s in SOURCES if s["kind"] != "telegram" or settings.NEWSBOT_USE_TELEGRAM]


def collect() -> dict:
    """Manbalardan faqat yangi materiallarni bazaga yozadi."""
    cutoff = timezone.now() - timedelta(days=settings.NEWSBOT_MAX_AGE_DAYS)
    stats = {"new": 0, "errors": []}

    for source in active_sources():
        try:
            raw_items = fetch_source(source)
        except Exception as exc:
            logger.warning("newsbot: %s o'qilmadi: %s", source["key"], exc)
            stats["errors"].append(source["key"])
            continue

        known = set(CollectedItem.objects.filter(url__in=[i.url for i in raw_items]).values_list("url", flat=True))
        first_run = not CollectedItem.objects.filter(source=source["key"]).exists()

        for raw in raw_items:
            if raw.url in known or len(raw.url) > 1000:
                continue
            known.add(raw.url)

            status = CollectedItem.NEW
            if raw.published_at is None:
                # Sanasi yo'q manba: birinchi ishga tushishda bor narsalar eski hisoblanadi.
                if first_run:
                    status = CollectedItem.SKIPPED
            elif raw.published_at < cutoff:
                continue
            if status == CollectedItem.NEW and source.get("general") and not is_candidate(raw.title, raw.text):
                continue

            CollectedItem.objects.create(
                source=source["key"], url=raw.url, title=raw.title[:500], text=raw.text,
                image_url=raw.image_url[:1000], published_at=raw.published_at, status=status,
            )
            stats["new"] += status == CollectedItem.NEW

    return stats


def _fill_from_article(item: CollectedItem, need_image: bool = False):
    """Feed'da yetishmagan sarlavha, matn yoki rasmni maqola sahifasidan oladi."""
    source = SOURCES_BY_KEY.get(item.source)
    has_text = item.title and len(item.text) >= MIN_TEXT_CHARS
    if not source or source["kind"] == "telegram" or (has_text and not (need_image and not item.image_url)):
        return
    try:
        title, text, image = fetch_article(source, item.url)
    except Exception as exc:
        logger.warning("newsbot: maqola o'qilmadi %s: %s", item.url, exc)
        return
    item.title = item.title or title[:500]
    if len(text) > len(item.text):
        item.text = text
    item.image_url = item.image_url or image[:1000]


def process() -> dict:
    """Yangi materiallarni AI ga ko'rsatadi, keraklilarini adminlarga yuboradi."""
    stats = {"drafted": 0, "rejected": 0, "failed": 0}
    if not (settings.GROQ_API_KEY and settings.NEWSBOT_TELEGRAM_TOKEN and settings.NEWSBOT_ADMIN_CHAT_IDS):
        logger.error("newsbot: GROQ_API_KEY, NEWSBOT_TELEGRAM_TOKEN yoki NEWSBOT_ADMIN_CHAT_IDS sozlanmagan")
        return stats
    items = CollectedItem.objects.filter(status=CollectedItem.NEW).order_by("created_at")

    for item in items[:settings.NEWSBOT_MAX_PER_RUN]:
        if not item.draft_content:
            _fill_from_article(item)
            if not (item.title or item.text):
                item.status, item.ai_reason = CollectedItem.FAILED, "Matn olinmadi"
                item.save()
                stats["failed"] += 1
                continue
            try:
                result = llm.review(source_name=source_name(item.source), title=item.title, text=item.text)
            except llm.LLMRateLimited:
                logger.warning("newsbot: Groq limiti, qolganlari keyingi safar")
                item.save()
                break
            except llm.LLMError as exc:
                logger.error("newsbot: AI xatosi %s: %s", item.url, exc)
                item.status, item.ai_reason = CollectedItem.FAILED, str(exc)[:500]
                item.save()
                stats["failed"] += 1
                continue

            item.ai_reason = result["reason"]
            if not result["relevant"]:
                item.status = CollectedItem.REJECTED
                item.save()
                stats["rejected"] += 1
                continue
            item.draft_title, item.draft_content = result["title"], result["content"]
            _fill_from_article(item, need_image=True)
            item.save()
            time.sleep(settings.NEWSBOT_LLM_PAUSE)

        # Yuborilmasa, material NEW bo'lib qoladi va keyingi safar AI siz qayta yuboriladi.
        try:
            item.telegram_messages = telegram.send_draft(item, source_name(item.source))
        except telegram.TelegramError as exc:
            logger.error("newsbot: Telegramga yuborilmadi: %s", exc)
            stats["failed"] += 1
            break
        item.status = CollectedItem.PENDING
        item.save()
        stats["drafted"] += 1

    return stats


def run() -> dict:
    return {**collect(), **process()}


def _owner() -> CustomUser:
    if settings.NEWSBOT_OWNER_PHONE:
        return CustomUser.objects.get(phone=settings.NEWSBOT_OWNER_PHONE)
    owner = CustomUser.objects.filter(is_superuser=True, is_active=True).order_by("id").first()
    if owner is None:
        raise CustomUser.DoesNotExist("Yangilik egasi uchun superuser topilmadi")
    return owner


def _attach_image(item: CollectedItem):
    # Rasm olinmasa ham yangilik chiqadi: tasdiq rasmga bog'liq bo'lmasligi kerak.
    try:
        data, extension = download_image(item.image_url)
        NewsMedia.objects.create(
            news=item.news, media_type="image",
            media_file=ContentFile(data, name=f"newsbot_{item.pk}{extension}"),
        )
    except Exception as exc:
        logger.warning("newsbot: rasm biriktirilmadi %s: %s", item.image_url, exc)


@transaction.atomic
def review(item_id: int, approve: bool, reviewer: str, with_image: bool = True) -> CollectedItem | None:
    """Admin qarorini qo'llaydi. Material allaqachon ko'rib chiqilgan bo'lsa None qaytaradi."""
    item = CollectedItem.objects.select_for_update().filter(pk=item_id, status=CollectedItem.PENDING).first()
    if item is None:
        return None
    if approve:
        item.news = News.objects.create(
            title=item.draft_title,
            content=f"{item.draft_content}\n\nManba: {source_name(item.source)} — {item.url}",
            owner=_owner(),
        )
        if with_image and item.image_url:
            _attach_image(item)
        item.status = CollectedItem.APPROVED
    else:
        item.status = CollectedItem.DECLINED
    item.reviewed_by = reviewer[:255]
    item.save()
    return item
