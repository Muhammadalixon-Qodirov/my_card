from rest_framework.routers import DefaultRouter

from .views import NewsViewSet, NewsLogViewSet


router = DefaultRouter()
router.register("news", NewsViewSet, basename="news")
router.register("news-logs", NewsLogViewSet, basename="news-log")

urlpatterns = router.urls
