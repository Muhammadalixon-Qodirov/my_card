from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import EmergencyNotification, Notification
from .serializers import EmergencyNotificationSerializer, NotificationSerializer


class IsSuperUserOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_superuser


class EmergencyNotificationViewSet(viewsets.ModelViewSet):
    queryset = EmergencyNotification.objects.all()
    serializer_class = EmergencyNotificationSerializer
    permission_classes = (IsSuperUserOrReadOnly,)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        """Bitta notificationni o'qilgan deb belgilash."""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response({"detail": "O'qilgan deb belgilandi."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        """Barcha notificationlarni o'qilgan deb belgilash."""
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": f"{updated} ta bildirishnoma o'qilgan deb belgilandi."})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """O'qilmagan bildirishnomalar soni."""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})
