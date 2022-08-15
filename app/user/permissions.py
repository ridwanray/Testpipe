from rest_framework import permissions
from django.contrib.auth import get_user_model


class IsSuperAdmin(permissions.BasePermission):
    """Allows access only to super admin users."""

    message = "Only Super Admins are authorized to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated and "SUPERADMIN" in request.user.roles
        )


class IsNotSuperAdmin(permissions.BasePermission):
    """Allows access only to non super admin users."""

    message = "Only non Super Admins are authorized to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated and "SUPERADMIN" not in request.user.roles
        )


class IsHRAdmin(permissions.BasePermission):
    """Allows access only to HR Admin users."""

    message = "Only HR Admins are authorized to perform this action."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and "HR_ADMIN" in request.user.roles)


class IsEmployee(permissions.BasePermission):
    """Allows access only to employees."""

    message = "Only Employees users are authorized to perform this action."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and "EMPLOYEE" in request.user.roles)
