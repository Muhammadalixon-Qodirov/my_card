from rest_framework import permissions, viewsets
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from .models import (
	Category, Module, Plan,
	DataCard, ModuleLog, DataCardLog,
	Test, TestAnswer
)
from .serializers import (
	CategorySerializer, ModuleSerializer,
	PlanSerializer, DataCardSerializer,
	ModuleLogSerializer, DataCardLogSerializer,
	TestSerializer, TestAnswerSerializer,
)
from .permissions import IsSuperUserForWrite



class OwnerCreateMixin:
	def perform_create(self, serializer):
		serializer.save(owner=self.request.user)


class CategoryViewSet(OwnerCreateMixin, viewsets.ModelViewSet):
	queryset = Category.objects.select_related("owner").all()
	serializer_class = CategorySerializer
	permission_classes = (IsSuperUserForWrite,)


class ModuleViewSet(OwnerCreateMixin, viewsets.ModelViewSet):
	serializer_class = ModuleSerializer
	permission_classes = (IsSuperUserForWrite,)

	def get_queryset(self):
		queryset = Module.objects.select_related("category", "owner")

		if not self.request.user or not self.request.user.is_authenticated:
			return queryset.annotate(
				total_data_cards=Value(0, output_field=IntegerField()),
				completed_data_cards=Value(0, output_field=IntegerField()),
				total_tests=Value(0, output_field=IntegerField()),
				answered_tests=Value(0, output_field=IntegerField()),
				wrong_answered_tests=Value(0, output_field=IntegerField()),
			)

		total_data_cards_subquery = DataCard.objects.filter(
			module_id=OuterRef("pk")
		).values("module_id").annotate(
			count=Count("id")
		).values("count")[:1]

		completed_data_cards_subquery = DataCardLog.objects.filter(
			data_card__module_id=OuterRef("pk"),
			user=self.request.user,
			is_completed=True,
		).values("data_card__module_id").annotate(
			count=Count("data_card_id", distinct=True)
		).values("count")[:1]

		total_tests_subquery = Test.objects.filter(
			module_id=OuterRef("pk")
		).values("module_id").annotate(
			count=Count("id")
		).values("count")[:1]

		answered_tests_subquery = TestAnswer.objects.filter(
			test__module_id=OuterRef("pk"),
			user=self.request.user,
		).values("test__module_id").annotate(
			count=Count("test_id", distinct=True)
		).values("count")[:1]

		wrong_answered_tests_subquery = TestAnswer.objects.filter(
			test__module_id=OuterRef("pk"),
			user=self.request.user,
			is_correct=False,
		).values("test__module_id").annotate(
			count=Count("test_id", distinct=True)
		).values("count")[:1]

		return queryset.annotate(
			total_data_cards=Coalesce(Subquery(total_data_cards_subquery, output_field=IntegerField()), Value(0)),
			completed_data_cards=Coalesce(
				Subquery(completed_data_cards_subquery, output_field=IntegerField()),
				Value(0),
			),
			total_tests=Coalesce(Subquery(total_tests_subquery, output_field=IntegerField()), Value(0)),
			answered_tests=Coalesce(Subquery(answered_tests_subquery, output_field=IntegerField()), Value(0)),
			wrong_answered_tests=Coalesce(
				Subquery(wrong_answered_tests_subquery, output_field=IntegerField()),
				Value(0),
			),
		)


class PlanViewSet(OwnerCreateMixin, viewsets.ModelViewSet):
	queryset = Plan.objects.select_related("modules", "owner").all()
	serializer_class = PlanSerializer
	permission_classes = (IsSuperUserForWrite,)


class DataCardViewSet(OwnerCreateMixin, viewsets.ModelViewSet):
	queryset = DataCard.objects.select_related("module", "plan", "owner").prefetch_related("media")
	serializer_class = DataCardSerializer
	permission_classes = (permissions.IsAuthenticated,)


class UserCreateMixin:
	def perform_create(self, serializer):
		serializer.save(user=self.request.user)


class ModuleLogViewSet(UserCreateMixin, viewsets.ModelViewSet):
	serializer_class = ModuleLogSerializer
	permission_classes = (permissions.IsAuthenticated,)

	def get_queryset(self):
		if getattr(self, "swagger_fake_view", False):
			return ModuleLog.objects.none()
		if not self.request.user.is_authenticated:
			return ModuleLog.objects.none()
		return ModuleLog.objects.select_related("module", "user").filter(user=self.request.user)


class DataCardLogViewSet(UserCreateMixin, viewsets.ModelViewSet):
	serializer_class = DataCardLogSerializer
	permission_classes = (permissions.IsAuthenticated,)

	def get_queryset(self):
		if getattr(self, "swagger_fake_view", False):
			return DataCardLog.objects.none()
		if not self.request.user.is_authenticated:
			return DataCardLog.objects.none()
		return DataCardLog.objects.select_related("data_card", "user").filter(user=self.request.user)


class TestViewSet(OwnerCreateMixin, viewsets.ModelViewSet):
	queryset = Test.objects.select_related("module", "owner").prefetch_related("options")
	serializer_class = TestSerializer
	permission_classes = (IsSuperUserForWrite,)


class TestAnswerViewSet(UserCreateMixin, viewsets.ModelViewSet):
	serializer_class = TestAnswerSerializer
	permission_classes = (permissions.IsAuthenticated,)

	def get_queryset(self):
		if getattr(self, "swagger_fake_view", False):
			return TestAnswer.objects.none()
		if not self.request.user.is_authenticated:
			return TestAnswer.objects.none()
		return TestAnswer.objects.select_related("test", "selected_option", "user").filter(user=self.request.user)
