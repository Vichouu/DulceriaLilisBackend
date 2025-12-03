from django import forms
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = "__all__"

        error_messages = {
            "sku": {"unique": "Ya existe un producto con ese SKU.", "invalid": "Formato de SKU inválido."},
            "ean_upc": {"unique": "Este EAN/UPC ya está registrado.", "invalid": "EAN/UPC debe tener 8/12/13/14 dígitos."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que los campos del formulario sean opcionales si el campo
        # del modelo correspondiente tiene blank=True, null=True o un default.
        for field_name, field in self.fields.items():
            model_field = self.Meta.model._meta.get_field(field_name)
            if model_field.blank or model_field.null or model_field.has_default():
                field.required = False

    def clean(self):
        data = super().clean()
        
        # Para campos numéricos que pueden ser 0 o null
        if not data.get('stock_minimo'):
            data['stock_minimo'] = 0  # Asigna 0 si está vacío
        if not data.get('stock_maximo'):
            data['stock_maximo'] = None  # Asigna None si está vacío y es opcional
        if not data.get('ean_upc'):
            data['ean_upc'] = None  # Asigna None si está vacío y es opcional
        
        # Validación de precio
        costo = data.get("costo_estandar")
        precio = data.get("precio_venta")
        if costo is not None and precio is not None and precio < costo:
            raise forms.ValidationError("El precio de venta no puede ser menor que el costo estándar.")
        
        return data