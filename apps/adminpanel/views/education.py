from django.db.models import Count, Prefetch, Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.education.models import (
    Category, DataCard, DataCardLog, DataCardMedia, Module, ModuleComment,
    ModuleFeedback, ModuleLog, ModuleQuestion, Score, Test, TestAnswer, TestOption,
)
from ..mixins import AdminAPIMixin, ReadAfterWriteMixin
from ..querysets import modules_queryset, sub_count
from ..serializers import (
    AdminCategorySerializer, AdminDataCardSerializer, AdminModuleCommentSerializer,
    AdminModuleFeedbackSerializer, AdminModuleLogSerializer, AdminModuleQuestionSerializer,
    AdminModuleSerializer, AdminScoreSerializer, AdminTestAnswerSerializer,
    AdminTestSerializer, ReplySerializer,
)


class OwnerCreateMixin:
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CategoryViewSet(AdminAPIMixin, ReadAfterWriteMixin, OwnerCreateMixin, viewsets.ModelViewSet):
    serializer_class = AdminCategorySerializer
    search_fields = ("name", "description")
    ordering_fields = ("id", "name", "created_at", "modules_count")
    ordering = ("name",)

    def get_queryset(self):
        return Category.objects.annotate(modules_count=sub_count(Module.objects.all(), "category"))


class ModuleViewSet(AdminAPIMixin, ReadAfterWriteMixin, OwnerCreateMixin, viewsets.ModelViewSet):
    serializer_class = AdminModuleSerializer
    filterset_fields = ("category",)
    search_fields = ("name", "description")
    ordering_fields = (
        "id", "name", "created_at", "score", "coin", "data_cards_count",
        "tests_count", "users_completed", "users_started",
    )
    ordering = ("category__name", "name")

    def get_queryset(self):
        qs = modules_queryset()
        state = self.request.query_params.get("content")
        if state == "empty":
            qs = qs.filter(data_cards_count=0)
        elif state == "no_tests":
            qs = qs.filter(tests_count=0)
        elif state == "ready":
            qs = qs.filter(data_cards_count__gt=0, tests_count__gt=0)
        return qs


class DataCardViewSet(AdminAPIMixin, ReadAfterWriteMixin, OwnerCreateMixin, viewsets.ModelViewSet):
    serializer_class = AdminDataCardSerializer
    filterset_fields = ("module", "module__category")
    search_fields = ("name", "description")
    ordering_fields = ("id", "name", "created_at")
    ordering = ("id",)  # ilova datacardlarni id bo'yicha tartiblaydi

    def get_queryset(self):
        return (
            DataCard.objects.select_related("module")
            .prefetch_related("media")
            .annotate(
                completed_count=sub_count(
                    DataCardLog.objects.filter(is_completed=True), "data_card", distinct="user"
                )
            )
        )

    @action(detail=True, methods=["delete"], url_path=r"media/(?P<media_id>\d+)")
    def delete_media(self, request, pk=None, media_id=None):
        deleted, _ = DataCardMedia.objects.filter(data_card_id=pk, pk=media_id).delete()
        if not deleted:
            return Response({"detail": "Media topilmadi."}, status=404)
        return Response(status=204)


class TestViewSet(AdminAPIMixin, ReadAfterWriteMixin, OwnerCreateMixin, viewsets.ModelViewSet):
    serializer_class = AdminTestSerializer
    filterset_fields = ("module", "is_special", "is_active", "module__category")
    search_fields = ("question",)
    ordering_fields = ("id", "created_at", "answers_count")
    ordering = ("created_at", "id")

    def get_queryset(self):
        options = TestOption.objects.annotate(answers_count=Count("answers")).order_by("id")
        return (
            Test.objects.select_related("module")
            .prefetch_related(Prefetch("options", queryset=options))
            .annotate(
                answers_count=sub_count(TestAnswer.objects.all(), "test"),
                correct_count=sub_count(TestAnswer.objects.filter(is_correct=True), "test"),
            )
        )


class ModuleQuestionViewSet(AdminAPIMixin, ReadAfterWriteMixin, viewsets.ModelViewSet):
    serializer_class = AdminModuleQuestionSerializer
    filterset_fields = ("module",)
    search_fields = ("text", "answer")
    ordering_fields = ("id", "created_at")
    ordering = ("created_at", "id")

    def get_queryset(self):
        return ModuleQuestion.objects.select_related("module")


class ModuleCommentViewSet(
    AdminAPIMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Foydalanuvchi izohlari (yuqori daraja) va ularga admin javoblari."""

    serializer_class = AdminModuleCommentSerializer
    filterset_fields = ("module", "user")
    search_fields = ("feedback", "user__phone", "user__first_name")
    ordering_fields = ("id", "created_at")
    ordering = ("-created_at",)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        replies = ModuleComment.objects.select_related("user").order_by("created_at")
        qs = (
            ModuleComment.objects.select_related("user", "module")
            .prefetch_related(Prefetch("replies", queryset=replies))
            .annotate(replies_count=Count("replies"))
        )
        if self.action == "list":
            qs = qs.filter(reply_to__isnull=True)
            answered = self.request.query_params.get("answered")
            if answered in ("1", "true"):
                qs = qs.filter(replies_count__gt=0)
            elif answered in ("0", "false"):
                qs = qs.filter(replies_count=0)
        return qs

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        parent = self.get_object()
        if parent.reply_to_id:
            parent = parent.reply_to
        serializer = ReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ModuleComment.objects.create(
            user=request.user,
            module=parent.module,
            feedback=serializer.validated_data["feedback"],
            reply_to=parent,
            is_admin_reply=True,
        )
        parent = self.get_queryset().get(pk=parent.pk)
        return Response(self.get_serializer(parent).data, status=201)


class ModuleFeedbackViewSet(
    AdminAPIMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = AdminModuleFeedbackSerializer
    filterset_fields = ("module", "reaction", "user")
    search_fields = ("comment", "user__phone", "module__name")
    ordering_fields = ("id", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = ModuleFeedback.objects.select_related("user", "module")
        if self.request.query_params.get("has_comment") in ("1", "true"):
            qs = qs.exclude(Q(comment__isnull=True) | Q(comment=""))
        return qs


class ScoreViewSet(AdminAPIMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminScoreSerializer
    filterset_fields = ("module", "user")
    ordering_fields = ("id", "score", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return Score.objects.select_related("user", "module")


class TestAnswerViewSet(AdminAPIMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminTestAnswerSerializer
    filterset_fields = ("test", "user", "is_correct", "test__module", "test__is_special")
    ordering_fields = ("id", "timestamp")
    ordering = ("-timestamp",)

    def get_queryset(self):
        return TestAnswer.objects.select_related("user", "test__module", "selected_option")


class ModuleLogViewSet(AdminAPIMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminModuleLogSerializer
    filterset_fields = ("module", "user", "is_completed")
    ordering_fields = ("id", "timestamp")
    ordering = ("-timestamp",)

    def get_queryset(self):
        return ModuleLog.objects.select_related("user", "module")
