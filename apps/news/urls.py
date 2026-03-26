from rest_framework.routers import DefaultRouter

from .views import NewsViewSet, NewsLogViewSet, FeedbackViewSet, AnswerViewSet


router = DefaultRouter()
router.register("news", NewsViewSet, basename="news")
router.register("news-logs", NewsLogViewSet, basename="news-log")
router.register("feedbacks", FeedbackViewSet, basename="feedback")
router.register("answers", AnswerViewSet, basename="answer")

urlpatterns = router.urls
