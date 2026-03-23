from rest_framework.routers import DefaultRouter

from .views import EmergencyNotificationViewSet, NotificationViewSet

router = DefaultRouter()
router.register("emergency", EmergencyNotificationViewSet, basename="emergency-notification")
router.register("", NotificationViewSet, basename="notification")

urlpatterns = router.urls
