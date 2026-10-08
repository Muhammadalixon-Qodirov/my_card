from django.urls import path
from rest_framework.routers import SimpleRouter

from .views.auth import AdminLoginView, AdminMeView
from .views.content import EmergencyViewSet, FAQViewSet, NewsViewSet
from .views.dashboard import ActivityView, DashboardView
from .views.economy import ChoiceViewSet, TransactionViewSet
from .views.education import (
    CategoryViewSet, DataCardViewSet, ModuleCommentViewSet, ModuleFeedbackViewSet,
    ModuleLogViewSet, ModuleQuestionViewSet, ModuleViewSet, ScoreViewSet,
    TestAnswerViewSet, TestViewSet,
)
from .views.inbox import FeedbackViewSet, NotificationViewSet
from .views.system import SystemLogsView, SystemView
from .views.users import UserViewSet

router = SimpleRouter()
router.register("users", UserViewSet, basename="admin-user")
router.register("categories", CategoryViewSet, basename="admin-category")
router.register("modules", ModuleViewSet, basename="admin-module")
router.register("data-cards", DataCardViewSet, basename="admin-data-card")
router.register("tests", TestViewSet, basename="admin-test")
router.register("module-questions", ModuleQuestionViewSet, basename="admin-module-question")
router.register("module-comments", ModuleCommentViewSet, basename="admin-module-comment")
router.register("module-feedbacks", ModuleFeedbackViewSet, basename="admin-module-feedback")
router.register("scores", ScoreViewSet, basename="admin-score")
router.register("test-answers", TestAnswerViewSet, basename="admin-test-answer")
router.register("module-logs", ModuleLogViewSet, basename="admin-module-log")
router.register("news", NewsViewSet, basename="admin-news")
router.register("faq", FAQViewSet, basename="admin-faq")
router.register("emergency", EmergencyViewSet, basename="admin-emergency")
router.register("feedbacks", FeedbackViewSet, basename="admin-feedback")
router.register("notifications", NotificationViewSet, basename="admin-notification")
router.register("transactions", TransactionViewSet, basename="admin-transaction")
router.register("choices", ChoiceViewSet, basename="admin-choice")

urlpatterns = [
    path("auth/login/", AdminLoginView.as_view(), name="admin-login"),
    path("auth/me/", AdminMeView.as_view(), name="admin-me"),
    path("dashboard/", DashboardView.as_view(), name="admin-dashboard"),
    path("activity/", ActivityView.as_view(), name="admin-activity"),
    path("system/", SystemView.as_view(), name="admin-system"),
    path("system/logs/", SystemLogsView.as_view(), name="admin-system-logs"),
] + router.urls
