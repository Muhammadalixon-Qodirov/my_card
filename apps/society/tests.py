from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import CustomUser
from .models import Choice, ChoiceMember


@override_settings(
	CACHES={
		"default": {
			"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
			"LOCATION": "society-tests",
		}
	}
)
class ChoiceJoinFlowTests(APITestCase):
	def setUp(self):
		self.owner = CustomUser.objects.create_user(
			phone="+998901111111",
			password="test-pass-123",
			first_name="Owner",
		)
		self.member = CustomUser.objects.create_user(
			phone="+998902222222",
			password="test-pass-123",
			first_name="Member",
		)
		self.client.force_authenticate(self.member)
		self.join_url = reverse("choice-join")

	def test_private_choice_generates_code(self):
		choice = Choice.objects.create(
			name="Private choice",
			owner=self.owner,
			award=10,
			is_public=False,
		)

		self.assertIsNotNone(choice.code)
		self.assertEqual(len(choice.code), 8)

	def test_public_choice_has_no_code(self):
		choice = Choice.objects.create(
			name="Public choice",
			owner=self.owner,
			award=10,
			is_public=True,
		)

		self.assertIsNone(choice.code)

	def test_multiple_public_choices_can_be_created(self):
		first = Choice.objects.create(
			name="Public 1",
			owner=self.owner,
			award=10,
			is_public=True,
		)
		second = Choice.objects.create(
			name="Public 2",
			owner=self.owner,
			award=20,
			is_public=True,
		)

		self.assertIsNone(first.code)
		self.assertIsNone(second.code)

	def test_public_choice_join_with_choice_id(self):
		choice = Choice.objects.create(
			name="Public join",
			owner=self.owner,
			award=10,
			is_public=True,
		)

		response = self.client.post(self.join_url, {"choice_id": choice.id}, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(ChoiceMember.objects.filter(choice=choice, user=self.member).exists())

	def test_private_choice_join_requires_code(self):
		choice = Choice.objects.create(
			name="Private join",
			owner=self.owner,
			award=10,
			is_public=False,
		)

		response = self.client.post(self.join_url, {"choice_id": choice.id}, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("detail", response.data)

	def test_private_choice_join_with_code(self):
		choice = Choice.objects.create(
			name="Private by code",
			owner=self.owner,
			award=10,
			is_public=False,
		)

		response = self.client.post(self.join_url, {"code": choice.code}, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(ChoiceMember.objects.filter(choice=choice, user=self.member).exists())
