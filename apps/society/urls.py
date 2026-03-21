from rest_framework.routers import DefaultRouter

from .views import ChoiceViewSet

router = DefaultRouter()
router.register("choices", ChoiceViewSet, basename="choice")

urlpatterns = router.urls
