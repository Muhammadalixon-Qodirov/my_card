from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.newsbot import pipeline, telegram
from apps.newsbot.fetchers import fetch_source


class Command(BaseCommand):
    help = "Newsbot: check - manbalarni tekshirish, run - bir marta ishga tushirish, webhook - Telegram webhook o'rnatish"

    def add_arguments(self, parser):
        parser.add_argument("action", choices=("check", "run", "webhook"))
        parser.add_argument("--url", help="webhook uchun sayt manzili, masalan https://mycard.e-investment.uz")

    def handle(self, *args, action, url=None, **options):
        getattr(self, f"do_{action}")(url)

    def do_check(self, url):
        for name in ("GROQ_API_KEY", "NEWSBOT_TELEGRAM_TOKEN", "NEWSBOT_ADMIN_CHAT_IDS", "NEWSBOT_WEBHOOK_SECRET"):
            self.stdout.write(f"{name}: {'bor' if getattr(settings, name) else 'YO`Q'}")
        for source in pipeline.active_sources():
            try:
                items = fetch_source(source)
                dated = sum(1 for i in items if i.published_at)
                self.stdout.write(f"OK   {source['key']:16} {len(items):4} ta ({dated} tasida sana bor)")
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"XATO {source['key']:16} {exc}"))

    def do_run(self, url):
        self.stdout.write(str(pipeline.run()))

    def do_webhook(self, url):
        if not url or not settings.NEWSBOT_WEBHOOK_SECRET:
            raise CommandError("--url va NEWSBOT_WEBHOOK_SECRET kerak")
        telegram.api(
            "setWebhook",
            url=f"{url.rstrip('/')}/api/v1/newsbot/telegram/webhook/",
            secret_token=settings.NEWSBOT_WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query"],
        )
        self.stdout.write(self.style.SUCCESS("Webhook o'rnatildi"))
