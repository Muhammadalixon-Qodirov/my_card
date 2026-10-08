from rest_framework.response import Response

from .pagination import AdminPagination
from .permissions import IsSuperUser


class AdminAPIMixin:
    """Admin panel uchun umumiy sozlamalar: faqat superuser, throttle yo'q."""

    permission_classes = (IsSuperUser,)
    throttle_classes = ()
    pagination_class = AdminPagination
    swagger_schema = None


class ReadAfterWriteMixin:
    """Yozishdan keyin obyektni annotatsiyalari bilan qayta o'qib qaytaradi."""

    write_serializer_class = None

    def get_serializer_class(self):
        if self.write_serializer_class and self.action in ("create", "update", "partial_update"):
            return self.write_serializer_class
        return self.serializer_class

    def read_response(self, instance, status_code=200):
        instance = self.get_queryset().get(pk=instance.pk)
        serializer = self.serializer_class(instance, context=self.get_serializer_context())
        return Response(serializer.data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.read_response(serializer.instance, 201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self.read_response(serializer.instance)
