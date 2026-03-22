from rest_framework.routers import DefaultRouter

from .views import EmergencyNotificationViewSet, NotificationViewSet

router = DefaultRouter()
router.register("", NotificationViewSet, basename="notification")
router.register("emergency", EmergencyNotificationViewSet, basename="emergency-notification")

urlpatterns = router.urls
