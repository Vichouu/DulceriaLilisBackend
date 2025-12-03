from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Q
from apps.products.models import Producto

valida_rut = RegexValidator(r'^[0-9Kk\.\-]{7,20}$', "RUT/NIF inválido")
valida_fono = RegexValidator(r'^[0-9+()\-\s]{6,30}$', 'Teléfono inválido')

class Proveedor(models.Model):
    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_BLOQUEADO = "BLOQUEADO"
    ESTADOS = ((ESTADO_ACTIVO, "Activo"), (ESTADO_BLOQUEADO, "Bloqueado"))

    rut_nif = models.CharField("RUT/NIF", max_length=20, unique=True, validators=[valida_rut])
    razon_social = models.CharField("Razón social", max_length=191)
    nombre_fantasia = models.CharField("Nombre de fantasía", max_length=191, blank=True)
    email = models.EmailField("Correo electrónico")
    telefono = models.CharField("Teléfono", max_length=30, blank=True, validators=[valida_fono])
    sitio_web = models.URLField("Sitio web", blank=True)

    direccion = models.CharField("Dirección", max_length=255, blank=True)
    ciudad = models.CharField("Ciudad", max_length=128, blank=True)
    pais = models.CharField("País", max_length=64, default="Chile")

    condiciones_pago = models.CharField("Condiciones de pago", max_length=120)
    moneda = models.CharField("Moneda", max_length=8, default="CLP")

    contacto_principal_nombre = models.CharField("Contacto principal (nombre)", max_length=120, blank=True)
    contacto_principal_email = models.EmailField("Contacto principal (email)", blank=True)
    contacto_principal_telefono = models.CharField("Contacto principal (teléfono)", max_length=30, blank=True, validators=[valida_fono])

    estado = models.CharField("Estado", max_length=10, choices=ESTADOS, default=ESTADO_ACTIVO)
    observaciones = models.TextField("Observaciones", blank=True)

    activo = models.BooleanField("Activo", default=True)
    creado_en = models.DateTimeField("Creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        ordering = ["razon_social"]
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        indexes = [
            models.Index(fields=["rut_nif"]),
            models.Index(fields=["razon_social"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["activo"]),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.rut_nif})"


class ProveedorProducto(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="productos", verbose_name="Proveedor")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="proveedores", verbose_name="Producto")

    costo = models.DecimalField("Costo", max_digits=12, decimal_places=4, validators=[MinValueValidator(0)])
    lead_time_dias = models.PositiveIntegerField("Lead time (días)", default=7, validators=[MinValueValidator(0), MaxValueValidator(365)])
    minimo_lote = models.DecimalField("Mínimo por lote", max_digits=12, decimal_places=3, default=1, validators=[MinValueValidator(0.001)])
    descuento_porcentaje = models.DecimalField("Descuento (%)", max_digits=5, decimal_places=2, null=True, blank=True,
                                               validators=[MinValueValidator(0), MaxValueValidator(100)])
    preferente = models.BooleanField("Proveedor preferente", default=False)

    class Meta:
        verbose_name = "Proveedor por Producto"
        verbose_name_plural = "Proveedores por Producto"
        unique_together = ("proveedor", "producto")
        indexes = [
            models.Index(fields=["producto"]),
            models.Index(fields=["proveedor"]),
            models.Index(fields=["preferente"]),
        ]
        constraints = [
            # Un proveedor preferente por producto
            models.UniqueConstraint(
                fields=["producto"], condition=Q(preferente=True),
                name="unico_proveedor_preferente_por_producto"
            ),
        ]

    def __str__(self):
        estrella = " ⭐" if self.preferente else ""
        return f"{self.proveedor} → {self.producto}{estrella}"
