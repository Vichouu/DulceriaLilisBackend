from django.contrib import admin
from .models import Proveedor, ProveedorProducto

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("rut_nif", "razon_social", "email", "telefono", "ciudad", "pais", "estado", "activo")
    list_filter = ("estado", "activo", "pais", "ciudad")
    search_fields = ("rut_nif", "razon_social", "nombre_fantasia", "email", "telefono")
    ordering = ("razon_social",)
    fieldsets = (
        ("Identificación", {"fields": ("rut_nif", "razon_social", "nombre_fantasia")}),
        ("Contacto principal", {"fields": ("email", "telefono", "sitio_web")}),
        ("Dirección", {"fields": ("direccion", "ciudad", "pais")}),
        ("Comercial", {"fields": ("condiciones_pago", "moneda")}),
        ("Contacto alternativo", {"fields": ("contacto_principal_nombre", "contacto_principal_email", "contacto_principal_telefono")}),
        ("Estado y tiempos", {"fields": ("estado", "activo", "creado_en", "actualizado_en")}),
        ("Notas", {"fields": ("observaciones",)}),
    )
    readonly_fields = ("creado_en", "actualizado_en")

@admin.register(ProveedorProducto)
class ProveedorProductoAdmin(admin.ModelAdmin):
    list_display = ("producto", "proveedor", "costo", "lead_time_dias", "minimo_lote", "descuento_porcentaje", "preferente")
    list_filter = ("preferente", "proveedor", "producto")
    search_fields = ("producto__nombre", "producto__sku", "proveedor__razon_social", "proveedor__rut_nif")
    ordering = ("producto__nombre", "proveedor__razon_social")
