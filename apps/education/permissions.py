from rest_framework import permissions


class IsSuperUserForWrite(permissions.BasePermission):
	def has_permission(self, request, view):
		if not request.user or not request.user.is_authenticated:
			return False
		if request.method in permissions.SAFE_METHODS:
			return True
		return request.user.is_superuser


class IsScoreOwner(permissions.BasePermission):
	def has_permission(self, request, view):
		return bool(request.user and request.user.is_authenticated)

	def has_object_permission(self, request, view, obj):
		if request.method in permissions.SAFE_METHODS:
			return True
		return obj.user == request.user or request.user.is_superuser
