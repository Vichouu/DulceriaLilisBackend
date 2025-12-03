from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from apps.products.models import Producto
from apps.suppliers.models import Proveedor


class Bodega(models.Model):
    nombre = models.CharField("Nombre", max_length=120, unique=True)
    ubicacion = models.CharField("Ubicación", max_length=191, blank=True)
    capacidad = models.DecimalField("Capacidad (uom)", max_digits=14, decimal_places=3, null=True, blank=True,
                                    validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Bodega"
        verbose_name_plural = "Bodegas"
        indexes = [models.Index(fields=["nombre"])]

    def __str__(self):
        return self.nombre


class Stock(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="stocks", verbose_name="Producto")
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name="stocks", verbose_name="Bodega")
    lote = models.CharField("Lote", max_length=100, blank=True, null=True)
    serie = models.CharField("Serie", max_length=100, blank=True, null=True)
    fecha_vencimiento = models.DateField("Fecha de vencimiento", blank=True, null=True)
    cantidad = models.DecimalField("Cantidad", max_digits=14, decimal_places=3, default=0)

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        unique_together = ("producto", "bodega", "lote", "serie", "fecha_vencimiento")
        indexes = [
            models.Index(fields=["producto", "bodega"]),
            models.Index(fields=["lote"]),
            models.Index(fields=["serie"]),
            models.Index(fields=["fecha_vencimiento"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(cantidad__gte=0), name="stock_cantidad_ge_0"),
        ]

    def __str__(self):
        ref = self.lote or self.serie or "-"
        return f"{self.producto} @ {self.bodega} = {self.cantidad} [{ref}]"


class MovimientoInventario(models.Model):
    TIPO_INGRESO = "INGRESO"
    TIPO_SALIDA = "SALIDA"
    TIPO_AJUSTE = "AJUSTE"
    TIPO_DEVOLUCION = "DEVOLUCION"
    TIPO_TRANSFERENCIA = "TRANSFERENCIA"
    TIPOS = (
        (TIPO_INGRESO, "Ingreso"),
        (TIPO_SALIDA, "Salida"),
        (TIPO_AJUSTE, "Ajuste"),
        (TIPO_DEVOLUCION, "Devolución"),
        (TIPO_TRANSFERENCIA, "Transferencia"),
    )

    tipo = models.CharField("Tipo", max_length=20, choices=TIPOS)
    fecha = models.DateTimeField("Fecha", auto_now_add=True)

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="movimientos", verbose_name="Producto")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Proveedor")
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="mov_salida", null=True, blank=True, verbose_name="Bodega origen")
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="mov_ingreso", null=True, blank=True, verbose_name="Bodega destino")

    cantidad = models.DecimalField("Cantidad", max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    lote = models.CharField("Lote", max_length=100, blank=True, null=True)
    serie = models.CharField("Serie", max_length=100, blank=True, null=True)
    fecha_vencimiento = models.DateField("Fecha de vencimiento", blank=True, null=True)

    observacion = models.TextField("Observación", blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Creado por")

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        indexes = [
            models.Index(fields=["tipo", "fecha"]),
            models.Index(fields=["producto"]),
            models.Index(fields=["bodega_origen"]),
            models.Index(fields=["bodega_destino"]),
            models.Index(fields=["lote"]),
            models.Index(fields=["serie"]),
        ]

    def __str__(self):
        return f"{self.tipo} {self.producto} {self.cantidad}"

    # Validaciones de negocio (coherencia)
    def clean(self):
        if self.tipo in (self.TIPO_INGRESO, self.TIPO_DEVOLUCION) and not self.bodega_destino:
            raise ValidationError("Debe indicar bodega destino para ingresos/devoluciones.")
        if self.tipo in (self.TIPO_SALIDA, self.TIPO_TRANSFERENCIA) and not self.bodega_origen:
            raise ValidationError("Debe indicar bodega origen para salidas/transferencias.")
        if self.producto.control_por_lote and not self.lote:
            raise ValidationError("El producto requiere control por lote.")
        if self.producto.control_por_serie and not self.serie:
            raise ValidationError("El producto requiere control por serie.")
        if self.producto.perecible and not self.fecha_vencimiento:
            raise ValidationError("El producto perecible debe tener fecha de vencimiento.")
        if self.fecha_vencimiento and self.fecha_vencimiento < timezone.now().date() and self.tipo in (self.TIPO_INGRESO, self.TIPO_TRANSFERENCIA):
            raise ValidationError("No se puede ingresar/transferir stock vencido.")
        if self.bodega_origen and self.bodega_destino and self.bodega_origen_id == self.bodega_destino_id and self.tipo == self.TIPO_TRANSFERENCIA:
            raise ValidationError("La transferencia debe ser entre bodegas distintas.")

    @transaction.atomic
    def aplicar_a_stock(self):
        """Aplica el movimiento al stock con transacción y bloqueo de filas."""
        def clave(bod):
            return dict(producto=self.producto, bodega=bod, lote=self.lote, serie=self.serie, fecha_vencimiento=self.fecha_vencimiento)

        if self.tipo in (self.TIPO_INGRESO, self.TIPO_DEVOLUCION):
            stk, _ = Stock.objects.select_for_update().get_or_create(**clave(self.bodega_destino))
            stk.cantidad = (stk.cantidad or 0) + self.cantidad
            stk.save()
            return

        if self.tipo == self.TIPO_SALIDA:
            stk = Stock.objects.select_for_update().get_or_create(**clave(self.bodega_origen))[0]
            if stk.cantidad < self.cantidad:
                raise ValidationError("Stock insuficiente para realizar la salida.")
            stk.cantidad -= self.cantidad
            stk.save()
            return

        if self.tipo == self.TIPO_AJUSTE:
            bod = self.bodega_destino or self.bodega_origen
            stk, _ = Stock.objects.select_for_update().get_or_create(**clave(bod))
            nuevo = (stk.cantidad or 0) + self.cantidad
            if nuevo < 0:
                raise ValidationError("El ajuste no puede dejar el stock en negativo.")
            stk.cantidad = nuevo
            stk.save()
            return

        if self.tipo == self.TIPO_TRANSFERENCIA:
            origen = Stock.objects.select_for_update().get_or_create(**clave(self.bodega_origen))[0]
            if origen.cantidad < self.cantidad:
                raise ValidationError("Stock insuficiente en bodega de origen.")
            destino, _ = Stock.objects.select_for_update().get_or_create(**clave(self.bodega_destino))
            origen.cantidad -= self.cantidad
            destino.cantidad = (destino.cantidad or 0) + self.cantidad
            origen.save(); destino.save()
            return
