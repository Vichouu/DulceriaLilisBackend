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
    capacidad = models.DecimalField(
        "Capacidad (uom)", max_digits=14, decimal_places=3,
        null=True, blank=True, validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = "Bodega"
        verbose_name_plural = "Bodegas"
        indexes = [models.Index(fields=["nombre"])]

    def __str__(self):
        return self.nombre


class Stock(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="stocks")
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name="stocks")
    lote = models.CharField(max_length=100, blank=True, null=True)
    serie = models.CharField(max_length=100, blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=3, default=0)

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
            models.CheckConstraint(check=models.Q(cantidad__gte=0), name="stock_cantidad_ge_0")
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

    tipo = models.CharField(max_length=20, choices=TIPOS)
    fecha = models.DateTimeField(auto_now_add=True)

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="movimientos")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    bodega_origen = models.ForeignKey(
        Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="mov_salida"
    )
    bodega_destino = models.ForeignKey(
        Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="mov_ingreso"
    )

    cantidad = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    lote = models.CharField(max_length=100, blank=True, null=True)
    serie = models.CharField(max_length=100, blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)

    observacion = models.TextField(blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.tipo} {self.producto} {self.cantidad}"

    # ==========================================================
    # VALIDACIONES
    # ==========================================================
    def clean(self):
        if self.tipo in (self.TIPO_INGRESO, self.TIPO_DEVOLUCION) and not self.bodega_destino:
            raise ValidationError("Debe indicar bodega destino para ingresos/devoluciones.")

        if self.tipo in (self.TIPO_SALIDA, self.TIPO_TRANSFERENCIA) and not self.bodega_origen:
            raise ValidationError("Debe indicar bodega origen para salidas/transferencias.")

        if self.bodega_origen and self.bodega_destino and self.tipo == self.TIPO_TRANSFERENCIA:
            if self.bodega_origen_id == self.bodega_destino_id:
                raise ValidationError("La transferencia debe ser entre bodegas distintas.")

    # ==========================================================
    #   LÓGICA DE STOCK DEFINITIVA (AJUSTE ABSOLUTO)
    # ==========================================================
    @transaction.atomic
    def aplicar_a_stock(self):

        def key(bod):
            return dict(
                producto=self.producto, bodega=bod,
                lote=self.lote, serie=self.serie,
                fecha_vencimiento=self.fecha_vencimiento
            )

        # INGRESO / DEVOLUCIÓN → suma
        if self.tipo in (self.TIPO_INGRESO, self.TIPO_DEVOLUCION):
            stk, _ = Stock.objects.select_for_update().get_or_create(**key(self.bodega_destino))
            stk.cantidad = (stk.cantidad or 0) + self.cantidad
            stk.save()
            return

        # SALIDA → resta con validación
        if self.tipo == self.TIPO_SALIDA:
            stk, _ = Stock.objects.select_for_update().get_or_create(**key(self.bodega_origen))
            if stk.cantidad < self.cantidad:
                raise ValidationError("Stock insuficiente para realizar la salida.")
            stk.cantidad -= self.cantidad
            stk.save()
            return

        # AJUSTE (ABSOLUTO) → stock final es EXACTAMENTE la cantidad ingresada
        if self.tipo == self.TIPO_AJUSTE:
            bod = self.bodega_destino or self.bodega_origen
            stk, _ = Stock.objects.select_for_update().get_or_create(**key(bod))
            if self.cantidad < 0:
                raise ValidationError("El ajuste no puede dejar el stock en negativo.")
            stk.cantidad = self.cantidad  # ← ABSOLUTO
            stk.save()
            return

        # TRANSFERENCIA → salida en origen + ingreso en destino
        if self.tipo == self.TIPO_TRANSFERENCIA:
            origen = Stock.objects.select_for_update().get_or_create(**key(self.bodega_origen))[0]
            if origen.cantidad < self.cantidad:
                raise ValidationError("Stock insuficiente en bodega origen.")
            destino, _ = Stock.objects.select_for_update().get_or_create(**key(self.bodega_destino))

            origen.cantidad -= self.cantidad
            destino.cantidad = (destino.cantidad or 0) + self.cantidad

            origen.save()
            destino.save()
            return
