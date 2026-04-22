from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import EmergencyNotification, Notification
from .serializers import EmergencyNotificationSerializer, NotificationSerializer


class EmergencyNotificationViewSet(viewsets.ModelViewSet):
    queryset = EmergencyNotification.objects.filter(is_active=True)
    serializer_class = EmergencyNotificationSerializer
    permission_classes = (permissions.IsAuthenticated, )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response({"detail": "O'qilgan deb belgilandi."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": f"{updated} ta bildirishnoma o'qilgan deb belgilandi."})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})
