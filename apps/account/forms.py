# apps/account/forms.py
import re
from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password  # lo dejamos por si lo necesitas luego


# ---- política de contraseñas (fuerte, en español) ----
def validate_password_policy(p: str):
    if len(p or "") < 12:
        raise ValidationError("La contraseña debe tener al menos 12 caracteres.")
    if not re.search(r"[A-Z]", p or ""):
        raise ValidationError("Debe incluir al menos una letra mayúscula.")
    if not re.search(r"[a-z]", p or ""):
        raise ValidationError("Debe incluir al menos una letra minúscula.")
    if not re.search(r"\d", p or ""):
        raise ValidationError("Debe incluir al menos un dígito.")
    if not re.search(r"[^A-Za-z0-9]", p or ""):
        raise ValidationError("Debe incluir al menos un símbolo (ej: @, #, $, !).")


class CustomPasswordResetForm(PasswordResetForm):
    """Puedes extender validaciones de email si lo necesitas."""
    pass

class CustomSetPasswordForm(SetPasswordForm):
    """Usada en reset/confirm."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].help_text = (
            "Mínimo 12 caracteres, con mayúscula, minúscula, dígito y símbolo."
        )

    def clean_new_password1(self):
        """
        Validación personalizada SOLO en español.
        Django NO se usa aquí porque da mensajes en inglés.
        """
        pwd = self.cleaned_data.get("new_password1")

        if not pwd:
            raise ValidationError("Debes ingresar la nueva contraseña.")

        # ❌ No usamos validate_password(pwd, self.user) para evitar mensajes en inglés

        # ✔ Validación propia (ESPAÑOL)
        validate_password_policy(pwd)

        return pwd

    def clean_new_password2(self):
        """
        Evitamos validadores en inglés en el campo de confirmación.
        Solo verificamos que coincida con new_password1.
        """
        pwd1 = self.cleaned_data.get('new_password1')
        pwd2 = self.cleaned_data.get('new_password2')

        if not pwd2:
            raise ValidationError("Debes confirmar la nueva contraseña.")

        if pwd1 and pwd2 and pwd1 != pwd2:
            raise ValidationError("Las contraseñas no coinciden.")

        return pwd2

    def _post_clean(self):
        """
        🔥 MUY IMPORTANTE:
        Django normalmente ejecuta aquí validate_password() con los
        AUTH_PASSWORD_VALIDATORS (que antes te tiraban mensajes en inglés).
        Lo anulamos para que SOLO se usen nuestras validaciones de arriba.
        """
        pass


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Usada en /password/change/ y soporta 'primer acceso' con invite_code.
    """

    invite_code = forms.CharField(
        required=False,
        max_length=12,
        label="Código de verificación (primer acceso)",
        help_text="Ingresa el código enviado a tu correo si es tu primer acceso."
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get("user")
        super().__init__(*args, **kwargs)

        self.fields["new_password1"].help_text = (
            "Mínimo 12 caracteres, con mayúscula, minúscula, dígito y símbolo."
        )

        if getattr(self.user, "must_change_password", False):
            self.fields["invite_code"].required = True

    def clean_new_password1(self):
        """
        Validación personalizada, solo español.
        """
        pwd = self.cleaned_data.get("new_password1")

        if not pwd:
            raise ValidationError("Debes ingresar la nueva contraseña.")

        validate_password_policy(pwd)

        return pwd

    def _post_clean(self):
        """
        🔥 Igual que en CustomSetPasswordForm:
        Django ejecuta aquí validate_password() con lo de settings.
        Lo anulamos para que NO agregue mensajes en inglés.
        """
        pass

    def clean(self):
        cleaned = super().clean()

        if getattr(self.user, "must_change_password", False):
            code = (cleaned.get("invite_code") or "").strip()
            real = (getattr(self.user, "invite_code", "") or "").strip()

            if code != real:
                raise ValidationError("El código de verificación no es válido.")

        return cleaned
