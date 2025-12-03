from django.contrib import admin
from .models import Bodega, Stock, MovimientoInventario
from .forms import MovimientoInventarioForm

@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "capacidad")
    search_fields = ("nombre", "ubicacion")
    ordering = ("nombre",)

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("producto", "bodega", "cantidad", "lote", "serie", "fecha_vencimiento")
    list_filter = ("bodega", "producto", "fecha_vencimiento")
    search_fields = ("producto__sku", "producto__nombre", "lote", "serie")
    ordering = ("producto__nombre",)
    readonly_fields = ()  

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    form = MovimientoInventarioForm
    list_display = ("tipo", "fecha", "producto", "cantidad", "bodega_origen", "bodega_destino", "lote", "serie", "fecha_vencimiento", "creado_por")
    list_filter = ("tipo", "bodega_origen", "bodega_destino", "producto", "fecha")
    search_fields = ("producto__sku", "producto__nombre", "lote", "serie", "observacion")
    ordering = ("-fecha",)
    fieldsets = (
        ("Datos del movimiento", {"fields": ("tipo", "fecha", "producto", "cantidad", "observacion", "creado_por")}),
        ("Ubicaciones", {"fields": ("bodega_origen", "bodega_destino")}),
        ("Trazabilidad", {"fields": ("lote", "serie", "fecha_vencimiento", "proveedor")}),
    )
    readonly_fields = ("fecha",)
