from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from decimal import Decimal

from apps.products.models import Producto
from apps.suppliers.models import Proveedor


class Bodega(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    ubicacion = models.CharField(max_length=191, blank=True)
    capacidad = models.DecimalField(
        max_digits=14, decimal_places=3,
        null=True, blank=True, validators=[MinValueValidator(0)]
    )

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
        unique_together = ("producto", "bodega", "lote", "serie", "fecha_vencimiento")

    def __str__(self):
        return f"{self.producto} @ {self.bodega} = {self.cantidad}"


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

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="mov_origen")
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="mov_destino")

    cantidad = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.000"))]  # Permitir 0
    )
    lote = models.CharField(max_length=100, blank=True, null=True)
    serie = models.CharField(max_length=100, blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    observacion = models.TextField(blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # -------------------------------
    # VALIDACIONES
    # -------------------------------
    def clean(self):
        # Para AJUSTE, solo se necesita una bodega, no importa cuál.
        if self.tipo == self.TIPO_AJUSTE:
            if not self.bodega_origen and not self.bodega_destino:
                raise ValidationError("Debe indicar una bodega para realizar el ajuste.")
            # Para ajuste, la cantidad puede ser 0, no necesita más validación aquí.
        else:
            # Para todos los demás tipos, la cantidad debe ser > 0
            if self.cantidad <= 0:
                raise ValidationError({"cantidad": "La cantidad debe ser mayor que cero."})

        if self.tipo in (self.TIPO_INGRESO, self.TIPO_DEVOLUCION) and not self.bodega_destino:
            raise ValidationError("Debe indicar bodega destino.")

        if self.tipo in (self.TIPO_SALIDA, self.TIPO_TRANSFERENCIA) and not self.bodega_origen:
            raise ValidationError("Debe indicar bodega origen.")

        # Para TRANSFERENCIA, se necesitan ambas bodegas.
        if self.tipo == self.TIPO_TRANSFERENCIA and not self.bodega_destino:
            raise ValidationError("Debe indicar bodega destino para la transferencia.")

        if (
            self.tipo == self.TIPO_TRANSFERENCIA
            and self.bodega_origen
            and self.bodega_destino
            and self.bodega_origen_id == self.bodega_destino_id
        ):
            raise ValidationError("La transferencia debe ser entre bodegas distintas.")

    # -------------------------------
    # LÓGICA DE STOCK
    # -------------------------------
    @transaction.atomic
    def aplicar_a_stock(self):

        def key(bod):
            return dict(
                producto=self.producto,
                bodega=bod,
                lote=self.lote,
                serie=self.serie,
                fecha_vencimiento=self.fecha_vencimiento,
            )

        # INGRESO + DEVOLUCIÓN
        if self.tipo in (self.TIPO_INGRESO, self.TIPO_DEVOLUCION):
            # Se usa get_or_create para añadir al stock existente o crear uno nuevo.
            stk, _ = Stock.objects.select_for_update().get_or_create(**key(self.bodega_destino))
            stk.cantidad = (stk.cantidad or Decimal("0")) + self.cantidad
            stk.save()
            return

        # SALIDA
        if self.tipo == self.TIPO_SALIDA:
            # Lógica de salida corregida:
            # 1. Validar contra el stock TOTAL del producto en la bodega.
            total_stock_bodega = Stock.objects.filter(
                producto=self.producto, bodega=self.bodega_origen
            ).aggregate(total=models.Sum('cantidad'))['total'] or Decimal('0')

            if total_stock_bodega < self.cantidad:
                raise ValidationError("Stock insuficiente para realizar salida.")

            # 2. Restar la cantidad de la bodega, descontando de los registros existentes de forma iterativa.
            cantidad_a_restar = self.cantidad
            stock_records = Stock.objects.select_for_update().filter(
                producto=self.producto,
                bodega=self.bodega_origen,
                cantidad__gt=0
            ).order_by('fecha_vencimiento', 'id') # Estrategia FIFO (First-In, First-Out)

            for stock_record in stock_records:
                if cantidad_a_restar <= 0:
                    break

                cantidad_a_descontar = min(stock_record.cantidad, cantidad_a_restar)
                stock_record.cantidad -= cantidad_a_descontar
                cantidad_a_restar -= cantidad_a_descontar
                stock_record.save()

            if cantidad_a_restar > 0:
                # Esta salvaguarda no debería activarse si la validación inicial es correcta.
                raise ValidationError("Error de consistencia: no se pudo descontar todo el stock de salida.")

            return

        # AJUSTE (SET ABSOLUTO)
        if self.tipo == self.TIPO_AJUSTE:
            bod = self.bodega_destino or self.bodega_origen
            # Lógica de ajuste corregida:
            # 1. Borra todo el stock existente para este producto en esta bodega.
            #    Esto simplifica el proceso y evita crear registros duplicados si hay lotes/series.
            Stock.objects.filter(producto=self.producto, bodega=bod).delete()

            # 2. Si la cantidad de ajuste es mayor que cero, crea un nuevo registro de stock.
            #    Si la cantidad es cero, el paso anterior ya dejó el stock en cero.
            if self.cantidad > 0:
                Stock.objects.create(
                    producto=self.producto,
                    bodega=bod,
                    cantidad=self.cantidad,
                    # Se puede asignar el lote/serie del ajuste si se desea, o dejarlo en blanco.
                )
            return

        # TRANSFERENCIA
        if self.tipo == self.TIPO_TRANSFERENCIA:
            # 1. Validar que haya stock suficiente en la bodega de origen.
            total_stock_origen = Stock.objects.filter(
                producto=self.producto, bodega=self.bodega_origen
            ).aggregate(total=models.Sum('cantidad'))['total'] or Decimal('0')

            if total_stock_origen < self.cantidad:
                raise ValidationError("Stock insuficiente en bodega origen.")

            # 2. Restar la cantidad de la bodega de origen (lógica idéntica a SALIDA para máxima robustez).
            cantidad_a_restar = self.cantidad
            stock_records_origen = Stock.objects.select_for_update().filter(
                producto=self.producto,
                bodega=self.bodega_origen,
                cantidad__gt=0
            ).order_by('fecha_vencimiento', 'id') # Estrategia FIFO

            for stock_record in stock_records_origen:
                if cantidad_a_restar <= 0:
                    break

                a_descontar = min(stock_record.cantidad, cantidad_a_restar)
                stock_record.cantidad -= a_descontar
                cantidad_a_restar -= a_descontar
                stock_record.save()

            if cantidad_a_restar > 0:
                # Esta situación no debería ocurrir si la validación inicial es correcta.
                # Es una salvaguarda.
                raise ValidationError(
                    "Error de consistencia: no se pudo descontar todo el stock de origen."
                )

            # 3. Sumar la cantidad a la bodega de destino.
            #    Se usa get_or_create para añadir al stock existente o crear uno nuevo.
            #    La función key() asegura que se agrupe por producto, bodega, lote, etc.
            stock_destino, _ = Stock.objects.select_for_update().get_or_create(**key(self.bodega_destino))
            stock_destino.cantidad = (stock_destino.cantidad or Decimal("0")) + self.cantidad
            stock_destino.save()
            return
