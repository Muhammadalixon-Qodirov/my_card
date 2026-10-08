import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import CustomUser
from apps.education.models import (
    Category, DataCard, DataCardLog, Module, ModuleComment, Score, Test, TestAnswer, TestOption,
)
from apps.news.models import Feedback
from apps.notifications.models import Notification
from apps.society.models import Choice
from apps.wallet.models import CoinTransaction

BASE = "/api/v1/admin-panel"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="mycard-test-media-"))
class AdminPanelTestCase(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone="+998900000001", password="admin-pass-123", first_name="Admin"
        )
        self.user = CustomUser.objects.create_user(
            phone="+998900000002", password="user-pass-123", first_name="Ali"
        )
        self.category = Category.objects.create(name="Moliya", owner=self.admin)
        self.module = Module.objects.create(
            name="Byudjet", category=self.category, owner=self.admin, score=100, coin=50
        )
        self.card = DataCard.objects.create(name="Dars 1", module=self.module, owner=self.admin)
        self.test = Test.objects.create(question="2+2?", module=self.module, owner=self.admin)
        self.right = TestOption.objects.create(test=self.test, option="4", is_correct=True)
        self.wrong = TestOption.objects.create(test=self.test, option="5", is_correct=False)
        self.client.force_authenticate(self.admin)


class AccessTests(AdminPanelTestCase):
    def test_anonymous_and_regular_users_are_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"{BASE}/dashboard/").status_code, 401)
        self.client.force_authenticate(self.user)
        for path in ("dashboard/", "users/", "modules/", "system/", "transactions/"):
            self.assertEqual(self.client.get(f"{BASE}/{path}").status_code, 403, path)

    def test_login_only_for_superusers(self):
        self.client.force_authenticate(None)
        ok = self.client.post(f"{BASE}/auth/login/", {"phone": self.admin.phone, "password": "admin-pass-123"})
        self.assertEqual(ok.status_code, 200)
        self.assertIn("access", ok.data)
        denied = self.client.post(f"{BASE}/auth/login/", {"phone": self.user.phone, "password": "user-pass-123"})
        self.assertEqual(denied.status_code, 403)
        bad = self.client.post(f"{BASE}/auth/login/", {"phone": self.admin.phone, "password": "nope"})
        self.assertEqual(bad.status_code, 400)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {ok.data['access']}")
        self.assertEqual(self.client.get(f"{BASE}/auth/me/").status_code, 200)

    def test_all_list_endpoints_respond(self):
        for path in (
            "users/", "categories/", "modules/", "data-cards/", "tests/", "module-questions/",
            "module-comments/", "module-feedbacks/", "scores/", "test-answers/", "module-logs/",
            "news/", "faq/", "emergency/", "feedbacks/", "feedbacks/summary/", "notifications/",
            "notifications/broadcasts/", "transactions/", "transactions/summary/", "choices/",
            "dashboard/", "activity/", "system/", "system/logs/",
        ):
            self.assertEqual(self.client.get(f"{BASE}/{path}").status_code, 200, path)

    def test_swagger_schema_still_builds(self):
        self.assertEqual(self.client.get("/swdoc/?format=openapi").status_code, 200)


class EducationTests(AdminPanelTestCase):
    def test_module_crud_and_counts(self):
        created = self.client.post(
            f"{BASE}/modules/", {"name": "Yangi", "category": self.category.id, "score": 10, "coin": 5}
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(Module.objects.get(pk=created.data["id"]).owner, self.admin)

        detail = self.client.get(f"{BASE}/modules/{self.module.id}/")
        self.assertEqual(detail.data["data_cards_count"], 1)
        self.assertEqual(detail.data["tests_count"], 1)
        self.assertEqual(len(self.client.get(f"{BASE}/modules/?content=empty").data["results"]), 1)

    def test_data_card_with_media_upload_and_removal(self):
        image = SimpleUploadedFile("a.png", b"\x89PNG fake", content_type="image/png")
        audio = SimpleUploadedFile("a.mp3", b"ID3 fake", content_type="audio/mpeg")
        created = self.client.post(
            f"{BASE}/data-cards/",
            {"name": "Dars 2", "module": self.module.id, "description": "Matn",
             "media_files": [image], "audio": audio},
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(len(created.data["media"]), 1)
        self.assertTrue(created.data["audio"])

        card_id, media_id = created.data["id"], created.data["media"][0]["id"]
        self.assertEqual(self.client.delete(f"{BASE}/data-cards/{card_id}/media/{media_id}/").status_code, 204)
        patched = self.client.patch(f"{BASE}/data-cards/{card_id}/", {"remove_audio": True}, format="json")
        self.assertEqual(patched.status_code, 200)
        self.assertFalse(patched.data["audio"])
        self.assertEqual(patched.data["media"], [])

    def test_test_update_keeps_user_answers(self):
        TestAnswer.objects.create(test=self.test, user=self.user, selected_option=self.right, is_correct=True)
        response = self.client.patch(
            f"{BASE}/tests/{self.test.id}/",
            {"question": "2+2 nechchi?", "options": [
                {"id": self.right.id, "option": "To'rt", "is_correct": True},
                {"id": self.wrong.id, "option": "Besh", "is_correct": False},
                {"option": "Olti", "is_correct": False},
            ]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["options"]), 3)
        self.assertEqual(TestAnswer.objects.filter(test=self.test).count(), 1)
        self.assertEqual(response.data["answers_count"], 1)

    def test_test_requires_single_correct_option(self):
        response = self.client.post(
            f"{BASE}/tests/",
            {"question": "?", "module": self.module.id, "options": [
                {"option": "a", "is_correct": True}, {"option": "b", "is_correct": True}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_comment_reply_is_marked_as_admin(self):
        comment = ModuleComment.objects.create(user=self.user, module=self.module, feedback="Savol")
        response = self.client.post(f"{BASE}/module-comments/{comment.id}/reply/", {"feedback": "Javob"})
        self.assertEqual(response.status_code, 201, response.data)
        reply = ModuleComment.objects.get(reply_to=comment)
        self.assertTrue(reply.is_admin_reply)
        self.assertEqual(reply.module, self.module)
        self.assertEqual(len(self.client.get(f"{BASE}/module-comments/?answered=0").data["results"]), 0)


class UserTests(AdminPanelTestCase):
    def test_list_is_annotated(self):
        Score.objects.create(user=self.user, module=self.module, score=80)
        CoinTransaction.objects.create(user=self.user, amount=40, transaction_type="earn")
        DataCardLog.objects.create(user=self.user, data_card=self.card, is_completed=True)
        rows = {r["id"]: r for r in self.client.get(f"{BASE}/users/?ordering=-total_score").data["results"]}
        self.assertEqual(rows[self.user.id]["total_score"], 80)
        self.assertEqual(rows[self.user.id]["coin_balance"], 40)
        detail = self.client.get(f"{BASE}/users/{self.user.id}/")
        self.assertEqual(detail.data["stats"]["data_cards_completed"], 1)

    def test_block_password_and_coins(self):
        blocked = self.client.patch(f"{BASE}/users/{self.user.id}/", {"is_active": False}, format="json")
        self.assertEqual(blocked.status_code, 200, blocked.data)
        self.assertFalse(blocked.data["is_active"])

        self.client.post(f"{BASE}/users/{self.user.id}/set-password/", {"password": "new-pass-456"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-pass-456"))

        added = self.client.post(
            f"{BASE}/users/{self.user.id}/coins/", {"amount": 30, "transaction_type": "earn"}
        )
        self.assertEqual(added.data["balance"], 30)
        over = self.client.post(
            f"{BASE}/users/{self.user.id}/coins/", {"amount": 99, "transaction_type": "spend"}
        )
        self.assertEqual(over.status_code, 400)

    def test_self_protection_and_content_owner_guard(self):
        self.assertEqual(
            self.client.patch(f"{BASE}/users/{self.admin.id}/", {"is_active": False}, format="json").status_code, 400
        )
        self.assertEqual(self.client.delete(f"{BASE}/users/{self.admin.id}/").status_code, 400)

        owner = CustomUser.objects.create_user(phone="+998900000003", password="x-pass-12345", first_name="O")
        Category.objects.create(name="Egali", owner=owner)
        self.assertEqual(self.client.delete(f"{BASE}/users/{owner.id}/").status_code, 409)
        self.assertEqual(self.client.delete(f"{BASE}/users/{self.user.id}/").status_code, 204)
        self.assertTrue(Module.objects.filter(pk=self.module.pk).exists())


class InboxAndEconomyTests(AdminPanelTestCase):
    def test_feedback_answer_resolves(self):
        feedback = Feedback.objects.create(
            feedback_type="problem", subject="Xato", message="Ishlamayapti", owner=self.user
        )
        response = self.client.post(f"{BASE}/feedbacks/{feedback.id}/answer/", {"answer": "Tuzatildi"})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "resolved")
        self.assertEqual(len(response.data["answers"]), 1)

    def test_broadcast_creates_and_recalls_notifications(self):
        response = self.client.post(
            f"{BASE}/notifications/broadcast/", {"title": "Salom", "body": "Yangilik", "audience": "all"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["recipients"], 2)
        self.assertEqual(Notification.objects.filter(notification_type="system").count(), 2)

        broadcasts = self.client.get(f"{BASE}/notifications/broadcasts/").data
        self.assertEqual(broadcasts[0]["recipients"], 2)
        deleted = self.client.delete(f"{BASE}/notifications/broadcasts/{response.data['broadcast_id']}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(Notification.objects.count(), 0)

    def test_choice_delete_refunds_owner(self):
        choice = Choice.objects.create(name="Tanlov", owner=self.user, award=70)
        self.assertEqual(self.client.get(f"{BASE}/choices/{choice.id}/leaderboard/").data, [])
        self.assertEqual(self.client.delete(f"{BASE}/choices/{choice.id}/?refund=1").status_code, 204)
        self.assertEqual(CoinTransaction.get_balance(self.user), 70)

    def test_choice_finish_without_members(self):
        choice = Choice.objects.create(name="Bo'sh", owner=self.user, award=10)
        response = self.client.post(f"{BASE}/choices/{choice.id}/finish/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["is_active"])
