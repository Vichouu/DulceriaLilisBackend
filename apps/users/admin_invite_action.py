# apps/users/admin_invite_action.py
from django.contrib import admin, messages
from django.apps import apps
from .utils_invite import invite_user_and_email  # <<< reutilizamos la utilidad

def _enviar_invitacion(modeladmin, request, queryset):
    enviados = 0
    for user in queryset:
        if not user.email:
            continue
        invite_user_and_email(user)
        enviados += 1

    modeladmin.message_user(
        request,
        f"Invitaciones enviadas: {enviados}",
        level=messages.SUCCESS
    )

_enviar_invitacion.short_description = "Enviar invitación (contraseña temporal + código)"

def inject_admin_action():
    Usuario = apps.get_model("users", "Usuario")
    if Usuario in admin.site._registry:
        modeladmin = admin.site._registry[Usuario]
        current_actions = list(modeladmin.actions or [])
        if not any(getattr(a, "__name__", "") == "_enviar_invitacion" for a in current_actions):
            current_actions.append(_enviar_invitacion)
            modeladmin.actions = current_actions
