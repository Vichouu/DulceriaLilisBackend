# apps/api/permissions.py
from rest_framework.permissions import BasePermission
from apps.users.models import Usuario

class IsAdminRole(BasePermission):
    """
    Permite acceso solo a usuarios autenticados con rol ADMIN
    o súperusuario.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Si es superuser, siempre puede
        if user.is_superuser:
            return True

        # Si tiene rol ADMIN (de tu modelo)
        try:
            return user.rol == Usuario.Roles.ADMIN
        except AttributeError:
            return False
