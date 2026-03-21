from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Foydalanuvchi bildirishnomalari.

    - GET  /notifications/          - Ro'yxat (faqat o'ziniki)
    - GET  /notifications/{id}/     - Tafsilot
    - POST /notifications/{id}/read/ - O'qilgan deb belgilash
    - POST /notifications/read-all/  - Barchasini o'qilgan deb belgilash
    - GET  /notifications/unread-count/ - O'qilmagan soni
    """

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
