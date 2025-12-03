# apps/users/apps.py
from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'

    def ready(self):
        # Si usas señales, impórtalas aquí (sin modelos).
        try:
            from .admin_invite_action import inject_admin_action
            inject_admin_action()
        except Exception:
            # No romper el arranque si algo falla al registrar la acción
            pass
