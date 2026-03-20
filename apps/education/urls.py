from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
	CategoryViewSet, ModuleViewSet,
	PlanViewSet, DataCardViewSet,
	ModuleLogViewSet, DataCardLogViewSet,
	TestViewSet, TestAnswerViewSet,
	ScoreViewSet, RatingListView
)


router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("modules", ModuleViewSet, basename="module")
router.register("plans", PlanViewSet, basename="plan")
router.register("data-cards", DataCardViewSet, basename="data-card")
router.register("module-logs", ModuleLogViewSet, basename="module-log")
router.register("data-card-logs", DataCardLogViewSet, basename="data-card-log")
router.register("tests", TestViewSet, basename="test")
router.register("test-answers", TestAnswerViewSet, basename="test-answer")
router.register("scores", ScoreViewSet, basename="score")


urlpatterns = router.urls + [
	path("rating/", RatingListView.as_view(), name="rating"),
]
