# === AÑADIR AL FINAL DE apps/account/views.py ===
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordChangeView
from django.urls import reverse_lazy
from .forms import CustomPasswordResetForm, CustomSetPasswordForm, CustomPasswordChangeForm

class PasswordResetRequestView(PasswordResetView):
    """
    Renderiza tu template 'password_reset_request.html' y envía el email con el enlace.
    """
    template_name = "password_reset_request.html"                  # tu template
    email_template_name = "emails/password_reset_email.txt"        # lo crearás en /templates/emails/
    subject_template_name = "emails/password_reset_subject.txt"    # lo crearás en /templates/emails/
    success_url = reverse_lazy("password_reset_done")              # ya está mapeado a login por urls.py
    form_class = CustomPasswordResetForm

class PasswordResetConfirmCustomView(PasswordResetConfirmView):
    """
    Usa tu template 'password_rest_confirm.html' para establecer la nueva contraseña
    validando la política.
    """
    template_name = "password_rest_confirm.html"  # tu template exacto
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy("password_reset_complete")  # redirige a login (urls.py)

class ChangePasswordView(PasswordChangeView):
    """
    Usa tu template 'change_password.html' (ya lo tienes). Si el usuario está en
    primer acceso (must_change_password), se exigirá el invite_code.
    """
    template_name = "change_password.html"  # tu template exacto
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy("password_change_done")  # redirige a login (urls.py)

    def form_valid(self, form):
        resp = super().form_valid(form)
        u = self.request.user
        # Si era primer acceso forzado, desactivar flag y limpiar invite_code
        if getattr(u, "must_change_password", False):
            u.must_change_password = False
            u.invite_code = ""
            u.save(update_fields=["must_change_password", "invite_code"])
        return resp
