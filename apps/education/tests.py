from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import CustomUser
from .models import Category, Module, Plan, DataCard, DataCardLog, Test, TestOption, TestAnswer


class ModuleProgressAPITests(APITestCase):
	def setUp(self):
		self.user = CustomUser.objects.create_user(
			phone="+998901234567",
			password="test-pass-123",
			first_name="Test",
		)
		self.client.force_authenticate(self.user)

		self.category = Category.objects.create(
			name="Matematika",
			owner=self.user,
		)
		self.module = Module.objects.create(
			name="Algebra",
			category=self.category,
			owner=self.user,
		)
		self.plan = Plan.objects.create(
			name="1-Plan",
			modules=self.module,
			owner=self.user,
		)
		self.data_card_1 = DataCard.objects.create(
			name="Dars 1",
			module=self.module,
			plan=self.plan,
			owner=self.user,
		)
		self.data_card_2 = DataCard.objects.create(
			name="Dars 2",
			module=self.module,
			plan=self.plan,
			owner=self.user,
		)

		self.test = Test.objects.create(
			question="2 + 2 nechiga teng?",
			module=self.module,
			owner=self.user,
		)
		self.correct_option = TestOption.objects.create(
			test=self.test,
			option="4",
			is_correct=True,
		)
		self.wrong_option = TestOption.objects.create(
			test=self.test,
			option="5",
			is_correct=False,
		)

	def _module_progress(self):
		response = self.client.get(reverse("module-detail", args=[self.module.id]))
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		return response.data["progress_percent"]

	def _complete_all_data_cards(self):
		DataCardLog.objects.create(user=self.user, data_card=self.data_card_1, is_completed=True)
		DataCardLog.objects.create(user=self.user, data_card=self.data_card_2, is_completed=True)

	def test_module_progress_is_50_when_all_data_cards_completed_but_test_not_answered(self):
		self._complete_all_data_cards()

		self.assertEqual(self._module_progress(), 50)

	def test_module_progress_is_100_when_test_is_answered_fully_correct(self):
		self._complete_all_data_cards()
		TestAnswer.objects.create(
			test=self.test,
			user=self.user,
			selected_option=self.correct_option,
			is_correct=True,
		)

		self.assertEqual(self._module_progress(), 100)

	def test_module_progress_scales_to_half_before_reading_is_completed(self):
		DataCardLog.objects.create(user=self.user, data_card=self.data_card_1, is_completed=True)

		self.assertEqual(self._module_progress(), 25)

	def test_module_progress_stays_50_if_any_test_answer_is_wrong(self):
		self._complete_all_data_cards()
		TestAnswer.objects.create(
			test=self.test,
			user=self.user,
			selected_option=self.wrong_option,
			is_correct=False,
		)

		self.assertEqual(self._module_progress(), 50)
