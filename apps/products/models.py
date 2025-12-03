from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError

valida_sku = RegexValidator(r'^[A-Z0-9\-_.]{3,50}$', "SKU inválido (usa A-Z, 0-9, -, _, .)")
valida_ean = RegexValidator(r'^\d{8}(\d{4,6})?$', "EAN/UPC debe ser 8/12/13/14 dígitos")

class Categoria(models.Model):
    nombre = models.CharField("Nombre", max_length=100, unique=True)
    descripcion = models.TextField("Descripción", blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        indexes = [models.Index(fields=["nombre"])]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    UOMS = (
        ("UN", "Unidad"),
        ("CAJA", "Caja"),
        ("KG", "Kilogramos"),
        ("GR", "Gramos"),
        ("PQ", "Paquete"),
        ("DISP", "Display"),
        ("BOL", "Bolsa"),
    )

    sku = models.CharField("SKU", max_length=50, unique=True, validators=[valida_sku])
    ean_upc = models.CharField("EAN/UPC", max_length=14, blank=True, null=True, unique=True, validators=[valida_ean])
    nombre = models.CharField("Nombre", max_length=191)
    descripcion = models.TextField("Descripción", blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos", verbose_name="Categoría")
    marca = models.CharField("Marca", max_length=100, blank=True)
    modelo = models.CharField("Modelo", max_length=100, blank=True)
    uom_compra = models.CharField("UoM de compra", max_length=10, choices=UOMS, default="UN")
    uom_venta = models.CharField("UoM de venta", max_length=10, choices=UOMS, default="UN")
    factor_conversion = models.DecimalField("Factor conversión", max_digits=10, decimal_places=4, default=1,
                                            validators=[MinValueValidator(0.0001)])

    costo_estandar = models.DecimalField("Costo estándar", max_digits=12, decimal_places=4, null=True, blank=True,
                                         validators=[MinValueValidator(0)])
    precio_venta = models.DecimalField("Precio de venta", max_digits=12, decimal_places=2, null=True, blank=True,
                                       validators=[MinValueValidator(0)])
    impuesto_iva = models.DecimalField("IVA (%)", max_digits=5, decimal_places=2, default=19,
                                       validators=[MinValueValidator(0), MaxValueValidator(25)])

    stock_minimo = models.DecimalField("Stock mínimo", max_digits=12, decimal_places=3, default=0,
                                       validators=[MinValueValidator(0)])
    stock_maximo = models.DecimalField("Stock máximo", max_digits=12, decimal_places=3, null=True, blank=True,
                                       validators=[MinValueValidator(0)])
    punto_reorden = models.DecimalField("Punto de reorden", max_digits=12, decimal_places=3, null=True, blank=True,
                                        validators=[MinValueValidator(0)])

    perecible = models.BooleanField("Perecible", default=False)
    control_por_lote = models.BooleanField("Control por lote", default=False)
    control_por_serie = models.BooleanField("Control por serie", default=False)

    url_imagen = models.URLField("URL Imagen", blank=True, null=True)
    url_ficha_tecnica = models.URLField("URL Ficha técnica", blank=True, null=True)

    activo = models.BooleanField("Activo", default=True)
    creado_en = models.DateTimeField("Creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["nombre"]),
            models.Index(fields=["categoria"]),
            models.Index(fields=["activo"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="prod_precio_mayor_igual_costo",
                check=models.Q(precio_venta__isnull=True) | models.Q(precio_venta__gte=models.F("costo_estandar"))
            ),
            models.CheckConstraint(
                name="prod_iva_0_25",
                check=models.Q(impuesto_iva__gte=0) & models.Q(impuesto_iva__lte=25)
            ),
            models.CheckConstraint(
                name="prod_stockmax_ge_min",
                check=(models.Q(stock_maximo__isnull=True) | models.Q(stock_maximo__gte=models.F("stock_minimo")))
            ),
            models.CheckConstraint(
                name="prod_reorden_ge_min",
                check=(models.Q(punto_reorden__isnull=True) | models.Q(punto_reorden__gte=models.F("stock_minimo")))
            ),
        ]

    def clean(self):
        """
        Validaciones a nivel de modelo para asegurar la lógica de negocio.
        """
        super().clean()
        # Validar que el precio de venta no sea menor que el costo estándar.
        # Se comprueba que ambos valores existan antes de comparar.
        if self.costo_estandar is not None and self.precio_venta is not None:
            if self.costo_estandar > self.precio_venta:
                raise ValidationError(
                    {'costo_estandar': 'El costo estándar no puede ser mayor que el precio de venta.'}
                )

    def save(self, *args, **kwargs):
        # Normaliza campos de texto antes de validar y guardar.
        if self.sku:
            self.sku = self.sku.strip().upper()
        if self.nombre:
            self.nombre = self.nombre.strip()
        # La validación completa (full_clean) es manejada por los ModelForms.
        # Llamarla aquí puede causar conflictos, especialmente con campos opcionales.
        # self.full_clean() # <- Eliminamos esta línea.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sku} - {self.nombre}"

    @property
    def alerta_bajo_stock(self):
        from transactional.models import Stock
        total = (Stock.objects
                 .filter(producto=self)
                 .aggregate(models.Sum("cantidad"))["cantidad__sum"] or 0)
        umbral = self.punto_reorden or self.stock_minimo or 0
        return total <= umbral
