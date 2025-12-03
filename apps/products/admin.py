from django.contrib import admin
from .models import Categoria, Producto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "sku", "nombre", "categoria", "precio_venta", "impuesto_iva",
        "stock_minimo", "punto_reorden", "perecible", "control_por_lote",
        "control_por_serie", "activo"
    )
    list_filter = ("categoria", "perecible", "control_por_lote", "control_por_serie", "activo")
    search_fields = ("sku", "nombre", "marca", "modelo", "ean_upc")
    ordering = ("nombre",)
    fieldsets = (
        ("Identificación", {"fields": ("sku", "ean_upc", "nombre", "descripcion", "categoria", "marca", "modelo")}),
        ("Unidades y conversión", {"fields": ("uom_compra", "uom_venta", "factor_conversion")}),
        ("Precios e impuestos", {"fields": ("costo_estandar", "precio_venta", "impuesto_iva")}),
        ("Stock y reorden", {"fields": ("stock_minimo", "stock_maximo", "punto_reorden")}),
        ("Controles especiales", {"fields": ("perecible", "control_por_lote", "control_por_serie")}),
        ("Recursos", {"fields": ("url_imagen", "url_ficha_tecnica")}),
        ("Estado y tiempos", {"fields": ("activo", "creado_en", "actualizado_en")}),
    )
    readonly_fields = ("creado_en", "actualizado_en")
