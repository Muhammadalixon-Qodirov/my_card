import json
import tempfile
from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.news.models import News
from . import fetchers, llm, pipeline, tasks, telegram
from .fetchers import RawItem
from .models import CollectedItem

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <item>
    <title><![CDATA[Soxta sayt orqali firibgarlik]]></title>
    <link>https://example.uz/a</link>
    <pubDate>Thu, 08 Oct 2026 09:57:16 +0000</pubDate>
    <description><![CDATA[<p>Qisqa</p>]]></description>
    <enclosure url="https://example.uz/cover.jpg" type="image/jpeg" length="1"/>
    <content:encoded><![CDATA[<p>Birinchi <b>xatboshi</b>.</p><script>x()</script><p>Ikkinchi.</p>]]></content:encoded>
  </item>
  <item>
    <title>Sanasiz</title>
    <link>https://example.uz/b</link>
    <description><![CDATA[Matn <img src="https://example.uz/inline.png?w=1&amp;h=2">]]></description>
  </item>
</channel>
</rss>"""

SOURCE = {"key": "test", "name": "Test manba", "kind": "rss", "url": "https://example.uz/feed"}
GENERAL = {**SOURCE, "key": "general", "general": True}
SETTINGS = dict(
    GROQ_API_KEY="k", NEWSBOT_TELEGRAM_TOKEN="t", NEWSBOT_ADMIN_CHAT_IDS=[111],
    NEWSBOT_WEBHOOK_SECRET="s3cret", NEWSBOT_LLM_PAUSE=0, NEWSBOT_OWNER_PHONE="",
)


def raw(url, title="Firibgarlar yangi usul topdi", days_old=0, dated=True, text="matn"):
    published = timezone.now() - timedelta(days=days_old) if dated else None
    return RawItem(url=url, title=title, text=text, published_at=published)


class FetcherTests(TestCase):
    def test_rss_is_parsed_to_plain_text(self):
        with mock.patch.object(fetchers, "http_get", return_value=RSS):
            first, second = fetchers.fetch_rss(SOURCE)

        self.assertEqual(first.url, "https://example.uz/a")
        self.assertEqual(first.title, "Soxta sayt orqali firibgarlik")
        self.assertEqual(first.text, "Birinchi xatboshi.\nIkkinchi.")
        self.assertEqual(first.published_at.isoformat(), "2026-10-08T09:57:16+00:00")
        self.assertIsNone(second.published_at)
        self.assertEqual(first.image_url, "https://example.uz/cover.jpg")
        self.assertEqual(second.image_url, "https://example.uz/inline.png?w=1&h=2")

    def test_dates_of_every_source_format(self):
        self.assertEqual(fetchers.parse_date("October 6, 2026 | 12:47PM").hour, 12)
        self.assertEqual(fetchers.parse_date("2026-10-08 17:55:00").utcoffset(), timedelta(hours=5))
        self.assertEqual(fetchers.parse_date("Tue, 06 Oct 2026 08:15:29").day, 6)
        self.assertEqual(fetchers.parse_date("2026-10-08T18:14:39+00:00").minute, 14)
        self.assertIsNone(fetchers.parse_date("yaqinda"))


@override_settings(**SETTINGS)
class CollectTests(TestCase):
    def collect(self, source, items):
        with mock.patch.object(pipeline, "active_sources", return_value=[source]), \
                mock.patch.object(pipeline, "fetch_source", return_value=items):
            return pipeline.collect()

    def test_only_new_items_are_stored_once(self):
        items = [raw("https://e.uz/1"), raw("https://e.uz/old", days_old=10)]
        self.assertEqual(self.collect(SOURCE, items)["new"], 1)
        self.assertEqual(self.collect(SOURCE, items + [raw("https://e.uz/2")])["new"], 1)
        self.assertEqual(
            sorted(CollectedItem.objects.values_list("url", flat=True)), ["https://e.uz/1", "https://e.uz/2"]
        )

    def test_general_source_needs_keyword(self):
        items = [
            raw("https://e.uz/1", title="Ob-havo ma'lumoti"),
            raw("https://e.uz/2", title="Кибермошенники"),
            raw("https://e.uz/3", title="Timsoh topildi", text="Olimlar buni firibgarlik emas deyishdi."),
            raw("https://e.uz/4", title="Bank ogohlantirdi", text="Firibgarlar fishing saytlar ochmoqda."),
            raw("https://e.uz/5", title="250 fuqaro kartasidan 3 mlrd so‘m o‘g‘irlandi"),
        ]
        self.collect(GENERAL, items)
        self.assertEqual(
            sorted(CollectedItem.objects.values_list("url", flat=True)),
            ["https://e.uz/2", "https://e.uz/4", "https://e.uz/5"],
        )

    def test_undated_backlog_is_skipped_on_first_run_only(self):
        self.collect(SOURCE, [raw("https://e.uz/1", dated=False)])
        self.collect(SOURCE, [raw("https://e.uz/1", dated=False), raw("https://e.uz/2", dated=False)])
        self.assertEqual(CollectedItem.objects.get(url="https://e.uz/1").status, CollectedItem.SKIPPED)
        self.assertEqual(CollectedItem.objects.get(url="https://e.uz/2").status, CollectedItem.NEW)

    def test_broken_source_does_not_stop_the_run(self):
        with mock.patch.object(pipeline, "active_sources", return_value=[SOURCE]), \
                mock.patch.object(pipeline, "fetch_source", side_effect=OSError("timeout")):
            self.assertEqual(pipeline.collect(), {"new": 0, "errors": ["test"]})


@override_settings(**SETTINGS)
class ProcessTests(TestCase):
    def setUp(self):
        self.item = CollectedItem.objects.create(source="test", url="https://e.uz/1", title="T", text="x" * 600)

    def process(self, verdict, send=None):
        with mock.patch.object(pipeline.llm, "review", return_value=verdict) as review, \
                mock.patch.object(pipeline.telegram, "send_draft", side_effect=send or [[[111, 5]]]) as send_draft:
            stats = pipeline.process()
        self.item.refresh_from_db()
        return stats, review, send_draft

    def test_relevant_item_goes_to_admins(self):
        verdict = {"relevant": True, "reason": "sxema", "title": "Sarlavha", "content": "Matn"}
        stats, _, _ = self.process(verdict)
        self.assertEqual(stats["drafted"], 1)
        self.assertEqual(self.item.status, CollectedItem.PENDING)
        self.assertEqual(self.item.telegram_messages, [[111, 5]])
        self.assertFalse(News.objects.exists())

    def test_irrelevant_item_is_rejected_without_telegram(self):
        _, _, send_draft = self.process({"relevant": False, "reason": "reklama", "title": "", "content": ""})
        self.assertEqual(self.item.status, CollectedItem.REJECTED)
        send_draft.assert_not_called()

    def test_failed_send_is_retried_without_second_ai_call(self):
        verdict = {"relevant": True, "reason": "", "title": "Sarlavha", "content": "Matn"}
        self.process(verdict, send=pipeline.telegram.TelegramError("down"))
        self.assertEqual(self.item.status, CollectedItem.NEW)
        _, review, _ = self.process(verdict)
        review.assert_not_called()
        self.assertEqual(self.item.status, CollectedItem.PENDING)

    @override_settings(GROQ_API_KEY="")
    def test_nothing_is_touched_without_config(self):
        self.assertEqual(pipeline.process(), {"drafted": 0, "rejected": 0, "failed": 0})
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, CollectedItem.NEW)


@override_settings(**SETTINGS, CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class ManualRunTests(TestCase):
    def run_task(self, stats):
        with mock.patch.object(tasks.pipeline, "run", return_value=stats), \
                mock.patch.object(tasks.telegram, "api") as api:
            tasks.run(111)
        return api.call_args.kwargs

    def test_admin_is_told_when_nothing_was_found(self):
        sent = self.run_task({"new": 0, "errors": ["ftc"], "drafted": 0, "rejected": 0, "failed": 0})
        self.assertEqual(sent["chat_id"], 111)
        self.assertIn("Mos yangi material topilmadi", sent["text"])
        self.assertIn("ftc", sent["text"])

    def test_admin_is_told_how_many_drafts_were_sent(self):
        sent = self.run_task({"new": 5, "errors": [], "drafted": 2, "rejected": 3, "failed": 0})
        self.assertIn("2 ta qoralama", sent["text"])

    def test_scheduled_run_stays_silent(self):
        with mock.patch.object(tasks.pipeline, "run", return_value={}), \
                mock.patch.object(tasks.telegram, "api") as api:
            tasks.run()
        api.assert_not_called()


@override_settings(**SETTINGS)
class LLMGuardTests(TestCase):
    def review(self, draft, text):
        body = {"choices": [{"message": {"content": json.dumps(
            {"relevant": True, "reason": "", "title": "Sarlavha", "content": draft}
        )}}]}
        response = mock.Mock(status_code=200, json=lambda: body)
        with mock.patch.object(llm.requests, "post", return_value=response):
            return llm.review(source_name="Test", title="Revolut leak", text=text)

    def test_invented_uzbekistan_is_refused(self):
        with self.assertRaises(llm.LLMError):
            self.review("O‘zbekistondagi kompaniyada ma'lumot sizdi.", "Revolut confirmed a breach in the UK.")

    def test_uzbekistan_from_the_source_is_kept(self):
        result = self.review("O'zbekistonda yangi sxema.", "В Узбекистане выявили новую схему.")
        self.assertTrue(result["relevant"])


@override_settings(**SETTINGS, MEDIA_ROOT=tempfile.mkdtemp(prefix="mycard-test-media-"))
class WebhookTests(TestCase):
    URL = "/api/v1/newsbot/telegram/webhook/"

    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone="+998900000001", password="admin-pass-123", first_name="Admin"
        )
        self.item = CollectedItem.objects.create(
            source="uzcert", url="https://e.uz/1", title="T", status=CollectedItem.PENDING,
            draft_title="Sarlavha", draft_content="Matn", telegram_messages=[[111, 5]],
        )

    def press(self, action, user_id=111, secret="s3cret"):
        update = {"callback_query": {"id": "1", "from": {"id": user_id, "username": "ali"},
                                     "data": f"nb:{action}:{self.item.pk}"}}
        with mock.patch("apps.newsbot.telegram.api") as api:
            response = self.client.post(self.URL, json.dumps(update), content_type="application/json",
                                        headers={"X-Telegram-Bot-Api-Secret-Token": secret})
        self.item.refresh_from_db()
        return response, api

    def test_approve_publishes_news_once(self):
        self.press("approve")
        self.press("approve")
        news = News.objects.get()
        self.assertEqual(news.title, "Sarlavha")
        self.assertEqual(news.content, "Matn\n\nManba: UZCERT — https://e.uz/1")
        self.assertEqual(news.owner, self.admin)
        self.assertEqual((self.item.status, self.item.news, self.item.reviewed_by),
                         (CollectedItem.APPROVED, news, "ali"))

    def test_stale_button_press_still_updates_the_message(self):
        def api(method, **payload):
            if method == "answerCallbackQuery":
                raise telegram.TelegramError("query is too old")

        update = {"callback_query": {"id": "1", "from": {"id": 111, "username": "ali"},
                                     "data": f"nb:approve:{self.item.pk}"}}
        with mock.patch("apps.newsbot.telegram.api", side_effect=api) as called:
            self.client.post(self.URL, json.dumps(update), content_type="application/json",
                             headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"})
        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(called.call_args_list[-1].args, ("editMessageText",))

    def press_with_image(self, action, download):
        self.item.image_url = "https://e.uz/cover.png"
        self.item.save()
        with mock.patch.object(pipeline, "download_image", side_effect=download) as download_image:
            self.press(action)
        return download_image

    def test_approve_attaches_the_source_image(self):
        self.press_with_image("approve", [(b"png-bytes", ".png")])
        media = News.objects.get().media.get()
        self.assertEqual(media.media_type, "image")
        self.assertTrue(media.media_file.name.endswith(".png"))
        self.assertEqual(media.media_file.read(), b"png-bytes")

    def test_approve_without_image_skips_the_download(self):
        download_image = self.press_with_image("noimg", [(b"png-bytes", ".png")])
        download_image.assert_not_called()
        self.assertEqual(self.item.status, CollectedItem.APPROVED)
        self.assertFalse(News.objects.get().media.exists())

    def test_broken_image_does_not_block_publishing(self):
        self.press_with_image("approve", OSError("404"))
        self.assertEqual(self.item.status, CollectedItem.APPROVED)
        self.assertFalse(News.objects.get().media.exists())

    def test_decline_publishes_nothing(self):
        self.press("decline")
        self.assertEqual(self.item.status, CollectedItem.DECLINED)
        self.assertFalse(News.objects.exists())

    def test_strangers_and_bad_secrets_cannot_approve(self):
        self.press("approve", user_id=999)
        response, api = self.press("approve", secret="wrong")
        self.assertEqual(response.status_code, 403)
        api.assert_not_called()
        self.assertEqual(self.item.status, CollectedItem.PENDING)
        self.assertFalse(News.objects.exists())
