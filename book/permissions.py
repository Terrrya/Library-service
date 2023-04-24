from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrAnyReadOnly(BasePermission):
    """Admin users can create/update/delete.
    All users (even those not authenticated) able to list"""

    def has_permission(self, request, view):
        return bool(
            (request.method in SAFE_METHODS)
            or (request.user and request.user.is_staff)
        )
