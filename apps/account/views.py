from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordChangeView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.cache import never_cache
from django.conf import settings

import logging
logger = logging.getLogger('login_secure')

from .forms import (
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    CustomPasswordChangeForm,
)


# ================================================================
# UTILIDADES
# ================================================================

def safe_reverse(*candidates, default="dashboard"):
    for name in candidates:
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    try:
        return reverse(default)
    except NoReverseMatch:
        return "/"


def get_redirect_for_role(user):
    rol = getattr(user, "rol", "") or ""

    if user.is_superuser or rol == "ADMIN":
        return safe_reverse("dashboard")

    role_map = {
        "COMPRAS": ("suppliers:list", "gestion_proveedores"),
        "INVENTARIO": ("products:list", "product_list"),
        "VENTAS": ("products:list", "product_list"),
        "PRODUCCION": ("transactional:list", "gestion_transacciones"),
        "FINANZAS": ("reports:panel",),
    }
    candidates = role_map.get(rol, ("dashboard",))
    return safe_reverse(*candidates, default="dashboard")


# ================================================================
# INICIO DE SESIÓN CON BLOQUEO POR INTENTOS
# ================================================================

@never_cache
def iniciar_sesion(request):

    # El mensaje de éxito de reseteo de contraseña ahora se maneja en la vista de confirmación.

    # si ya está logueado
    if request.user.is_authenticated:
        return redirect(get_redirect_for_role(request.user))

    # PETICIÓN POST
    if request.method == "POST":

        usuario = request.POST.get("username", "")
        contrasena = request.POST.get("password", "")

        ip = request.META.get('REMOTE_ADDR', 'desconocida')
        logger.info(f"Intento de login: usuario={usuario}, ip={ip}")

        # Intentamos obtener usuario para revisar bloqueo
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            u = User.objects.get(username=usuario)
        except User.DoesNotExist:
            u = None

        # ------------------------------------------------
        # VALIDACIÓN DE BLOQUEO
        # ------------------------------------------------
        if u and u.bloqueado_hasta:
            if timezone.now() < u.bloqueado_hasta:
                segundos = int((u.bloqueado_hasta - timezone.now()).total_seconds())
                minutos = segundos // 60
                resto = segundos % 60

                messages.error(
                    request,
                    f"Demasiados intentos fallidos. Intenta nuevamente en {minutos}m {resto}s."
                )
                return render(request, "login.html")

        # Procesar autenticación
        user = authenticate(request, username=usuario, password=contrasena)

        # ------------------------------------------------
        # LOGIN CORRECTO
        # ------------------------------------------------
        if user is not None:

            # limpiar contador
            user.intentos_fallidos_login = 0
            user.bloqueado_hasta = None
            user.save(update_fields=["intentos_fallidos_login", "bloqueado_hasta"])

            if getattr(user, "estado", "activo") != "activo" or not getattr(user, "activo", True):
                logger.info(f"Login bloqueado (usuario inactivo): usuario={usuario}, ip={ip}")
                messages.error(request, "Tu usuario está desactivado. Contacta al administrador.")
                return render(request, "login.html")

            login(request, user)

            logger.info(f"Login exitoso: usuario={usuario}, ip={ip}")

            next_url = request.POST.get("next") or request.GET.get("next")
            if (user.is_superuser or getattr(user, "rol", "") == "ADMIN") and next_url:
                return redirect(next_url)

            return redirect(get_redirect_for_role(user))

        # ------------------------------------------------
        # LOGIN FALLIDO
        # ------------------------------------------------
        logger.info(f"Login fallido: usuario={usuario}, ip={ip}")

        if u:
            u.intentos_fallidos_login += 1

            if u.intentos_fallidos_login >= 5:
                u.bloqueado_hasta = timezone.now() + timedelta(minutes=1)
                u.save(update_fields=["intentos_fallidos_login", "bloqueado_hasta"])

                messages.error(
                    request,
                    "Has superado el número máximo de intentos. "
                    "Tu cuenta está bloqueada por 1 minuto."
                )
                return render(request, "login.html")

            u.save(update_fields=["intentos_fallidos_login"])

        messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "login.html")


# ================================================================
# CERRAR SESIÓN
# ================================================================

def cerrar_sesion(request):
    logout(request)
    return redirect("login")


# ================================================================
# GATE MODULE
# ================================================================

@login_required
def module_gate_view(request, app_slug: str):
    return render(request, "module_gate.html", {"app_slug": app_slug})


# ================================================================
# PASSWORD RESET
# ================================================================

class PasswordResetRequestView(PasswordResetView):
    template_name = "password_reset_request.html"
    email_template_name = "emails/password_reset_email.txt"
    html_email_template_name = "emails/password_reset_email.html"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")
    form_class = CustomPasswordResetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        domain = getattr(settings, "PASSWORD_RESET_DOMAIN", None) or self.request.get_host()
        protocol = getattr(settings, "PASSWORD_RESET_PROTOCOL", None)
        if not protocol:
            protocol = "https" if self.request.is_secure() else "http"

        context["domain"] = domain
        context["protocol"] = protocol
        return context

    def form_valid(self, form):
        # Si la petición es AJAX (desde nuestro script), devolvemos JSON.
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            # Usar el dominio de producción definido en settings.py
            domain = getattr(settings, "PASSWORD_RESET_DOMAIN", self.request.get_host())

            form.save(
                domain_override=domain,
                use_https=self.request.is_secure(),
                email_template_name=self.email_template_name,
                html_email_template_name=self.html_email_template_name,
                subject_template_name=self.subject_template_name,
                request=self.request,
            )
            return JsonResponse({'status': 'success', 'message': 'Correo enviado.'})

        # Comportamiento normal si no es AJAX (no debería ocurrir con el nuevo script)
        super().form_valid(form)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # Si la petición es AJAX y el formulario es inválido (ej: email no existe),
        # devolvemos los errores en formato JSON.
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            # Usamos el primer error del campo 'email' como mensaje principal.
            error_message = form.errors.get('email', ['Error desconocido.'])[0]
            return JsonResponse({'status': 'error', 'message': error_message}, status=400)
        return super().form_invalid(form)


class PasswordResetConfirmCustomView(PasswordResetConfirmView):
    template_name = "password_reset_confirm.html"
    form_class = CustomSetPasswordForm

    def form_valid(self, form):
        user = form.save()
        user.save()  # Asegurarse de que la nueva contraseña se guarde en la BD
        logout(self.request)
        
        success_message = "Tu contraseña ha sido actualizada correctamente. Por favor inicia sesión."
        login_url = reverse("login")

        # Si la petición es AJAX, devolvemos la URL de redirección en JSON
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "ok": True, 
                "message": success_message, # Enviamos el mensaje específico
                "redirect": login_url
            })

        # Si no, hacemos una redirección normal
        messages.success(self.request, success_message) # Mantenemos el mensaje para el flujo sin JS
        return redirect(login_url)

class ChangePasswordView(PasswordChangeView):
    template_name = "change_password.html"
    form_class = CustomPasswordChangeForm

    def get_success_url(self):
        return get_redirect_for_role(self.request.user)

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.save()

        if getattr(user, "must_change_password", False):
            user.must_change_password = False
            user.invite_code = ""
            user.save(update_fields=["must_change_password", "invite_code"])

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "ok": True,
                "redirect": self.get_success_url()
            })

        return super().form_valid(form)