from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Upper
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# Validador para celular chileno:
# - Acepta +569XXXXXXXX
# - Acepta 9XXXXXXXXX  (9 dígitos, sin +56)
telefono_chile_validator = RegexValidator(
    regex=r'^(\+569\d{8}|9\d{8})$',
    message='Formato inválido: usa +569XXXXXXXX o 9XXXXXXXXX (9 dígitos).'
)


class Usuario(AbstractUser):
    intentos_fallidos_login = models.IntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrador')
        COMPRAS = 'COMPRAS', _('Operador de Compras')
        INVENTARIO = 'INVENTARIO', _('Operador de Inventario')
        PRODUCCION = 'PRODUCCION', _('Operador de Producción')
        VENTAS = 'VENTAS', _('Operador de Ventas')
        FINANZAS = 'FINANZAS', _('Analista Financiero')
        

    class Estados(models.TextChoices):
        ACTIVO = 'activo', _('Activo')
        INACTIVO = 'inactivo', _('Inactivo')
        BLOQUEADO = 'bloqueado', _('Bloqueado')

    # Importante: redefinimos email para evitar choques y asegurar índice en MySQL
    email = None
    email = models.EmailField(
        _("email address"),
        max_length=191,
        unique=True,        # único en BD
        blank=False         # requerido (tus vistas ya lo exigen)
    )

    telefono = models.CharField(
        "Teléfono",
        max_length=30,
        blank=True,         # opcional en formularios
        validators=[telefono_chile_validator],
    )

    rol = models.CharField(
        _("Rol"),
        max_length=20,
        choices=Roles.choices,
        default=Roles.VENTAS
    )

    # Estado que tu UI/vistas usan
    estado = models.CharField(
        _("Estado"),
        max_length=10,
        choices=Estados.choices,
        default=Estados.ACTIVO,
        db_index=True
    )

    area = models.CharField("Área/Unidad", max_length=120, blank=True)
    mfa_habilitado = models.BooleanField("MFA habilitado", default=False)

    # Puedes mantener este boolean si lo necesitas aparte del 'estado'
    activo = models.BooleanField("Activo", default=True)

    # Campos para invitación/cambio forzado
    invite_code = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        help_text="Código de verificación para primer acceso"
    )
    must_change_password = models.BooleanField(
        default=False,
        help_text="Forzar cambio de contraseña al iniciar"
    )

    def clean(self):
        """
        Normaliza y valida el teléfono:
        - Acepta +569XXXXXXXX o 9XXXXXXXXX (sin espacios).
        - Lo guarda SIEMPRE como +569XXXXXXXX.
        - Impide teléfonos duplicados.
        """
        super().clean()

        tel = (self.telefono or "").strip()
        if not tel:
            # Si está vacío, no obligamos a tener teléfono.
            return

        # Quitar espacios en blanco
        tel = tel.replace(" ", "")

        # Normalizar
        if tel.startswith("+569") and len(tel) == 12 and tel[4:].isdigit():
            normalizado = tel
        elif tel.startswith("9") and len(tel) == 9 and tel.isdigit():
            # De 9XXXXXXXXX pasamos a +569XXXXXXXX
            normalizado = "+56" + tel
        else:
            raise ValidationError({
                "telefono": "Formato inválido: usa +569XXXXXXXX o 9XXXXXXXXX (9 dígitos)."
            })

        # Verificar unicidad (otro usuario con el mismo teléfono)
        qs = Usuario.objects.filter(telefono=normalizado)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({
                "telefono": "Ya existe un usuario con este número de teléfono."
            })

        # Guardamos siempre en formato normalizado
        self.telefono = normalizado

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        indexes = [
            models.Index(fields=["username"]),
            # índice case-insensitive para búsquedas por email:
            models.Index(Upper("email"), name="user_email_upper_idx"),
            models.Index(fields=["activo"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(activo__in=[True, False]),
                name="usr_activo_bool"
            ),
        ]
        ordering = ["username"]

    def __str__(self):
        nombre = (self.first_name + " " + self.last_name).strip()
        return f"{self.username} ({nombre})" if nombre else self.username