from rest_framework import permissions, viewsets

from .models import (
	Category,
	Module,
	Plan,
	DataCard,
	ModuleLog,
	DataCardLog,
	Test,
	TestAnswer,
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
	queryset = Module.objects.select_related("category", "owner").all()
	serializer_class = ModuleSerializer
	permission_classes = (IsSuperUserForWrite,)


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
