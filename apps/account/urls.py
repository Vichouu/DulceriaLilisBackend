from django.urls import path
from django.views.generic import RedirectView

from . import views  # tus vistas existentes (iniciar_sesion, cerrar_sesion, module_gate_view)

# Vistas nuevas que ya agregamos en apps/account/views.py
# (PasswordResetRequestView, PasswordResetConfirmCustomView, ChangePasswordView)
from .views import (
    PasswordResetRequestView,
    PasswordResetConfirmCustomView,
    ChangePasswordView,
)

urlpatterns = [
    # === TUS RUTAS EXISTENTES ===
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('modulo/<str:app_slug>/', views.module_gate_view, name='module_gate'),

    # === NUEVO: Recuperar contraseña ===
    # Usa tu template: apps/account/templates/password_reset_request.html
    path('password/reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),

    # Tras enviar el correo (en el flujo sin JS), redirigimos directamente al login.
    path('password/reset/done/',
        RedirectView.as_view(pattern_name='login', permanent=False),
        name='password_reset_done',
    ),

    # Confirmar (crear nueva) usando tu template: password_reset_confirm.html
    path(
        'password/reset/confirm/<uidb64>/<token>/',
        PasswordResetConfirmCustomView.as_view(),
        name='password_reset_confirm',
    ),

    # Al completar el cambio vía token, de vuelta al login (sin plantilla "complete")
    path(
        'password/reset/complete/',
        RedirectView.as_view(pattern_name='login', permanent=False), # Ahora la vista de confirmación redirige aquí
        name='password_reset_complete',
    ),

    # === NUEVO: Cambiar contraseña (usuario autenticado) ===
    # Usa tu template: apps/account/templates/change_password.html
    path('password/change/', ChangePasswordView.as_view(), name='password_change'),

    # Tras cambiarla, redirigimos al login (sin plantilla "change_done")
    path(
        'password/change/done/',
        RedirectView.as_view(pattern_name='login', permanent=False),
        name='password_change_done',
    ),
]
