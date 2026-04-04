from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
	CategoryViewSet, ModuleViewSet,
	DataCardViewSet,
	ModuleLogViewSet, DataCardLogViewSet,
	TestViewSet, SpecialTestViewSet, TestAnswerViewSet,
	ScoreViewSet, RatingListView, ModuleFeedbackViewSet, ModuleQuestionViewSet, ModuleCommentViewSet
)


router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("modules", ModuleViewSet, basename="module")
router.register("data-cards", DataCardViewSet, basename="data-card")
router.register("module-logs", ModuleLogViewSet, basename="module-log")
router.register("data-card-logs", DataCardLogViewSet, basename="data-card-log")
router.register("tests", TestViewSet, basename="test")
router.register("special-tests", SpecialTestViewSet, basename="special-test")
router.register("test-answers", TestAnswerViewSet, basename="test-answer")
router.register("scores", ScoreViewSet, basename="score")
router.register("module-feedbacks", ModuleFeedbackViewSet, basename="module-feedback")


urlpatterns = router.urls + [
	path("rating/", RatingListView.as_view(), name="rating"),
	path("modules/<int:module_id>/questions/", ModuleQuestionViewSet.as_view({"get": "list"}), name="module-questions"),
	path("modules/<int:module_id>/comments/", ModuleCommentViewSet.as_view({
		"get": "list",
		"post": "create"
	}), name="module-comments"),
	path("modules/<int:module_id>/comments/<int:pk>/", ModuleCommentViewSet.as_view({
		"get": "retrieve",
		"patch": "partial_update",
		"delete": "destroy"
	}), name="module-comment-detail"),
]
