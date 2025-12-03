from django import forms
from django.core.exceptions import ValidationError
from .models import MovimientoInventario

class MovimientoInventarioForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        mov = MovimientoInventario(**{f: cleaned.get(f) for f in cleaned})
        # Reutiliza las validaciones del modelo (en español)
        mov.clean()
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit)
        # Aplica el movimiento al stock inmediatamente (empresa real)
        obj.aplicar_a_stock()
        return obj
