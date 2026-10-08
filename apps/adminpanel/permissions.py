from rest_framework import permissions


class IsSuperUser(permissions.BasePermission):
    message = "Bu bo'lim faqat administratorlar uchun."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_superuser)
