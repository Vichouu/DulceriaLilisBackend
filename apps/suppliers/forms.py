from django import forms
from .models import ProveedorProducto

class ProveedorProductoForm(forms.ModelForm):
    class Meta:
        model = ProveedorProducto
        fields = "__all__"

    def clean(self):
        data = super().clean()
        # ejemplo extra: descuento no puede superar 50% si no es preferente (regla política)
        desc = data.get("descuento_porcentaje")
        pref = data.get("preferente")
        if desc is not None and desc > 50 and not pref:
            raise forms.ValidationError("Descuentos mayores al 50% requieren que el proveedor sea preferente.")
        return data
