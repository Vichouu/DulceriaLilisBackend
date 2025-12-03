from django import forms
from .models import Usuario

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'first_name', 'last_name', 'telefono',
                  'rol', 'estado', 'mfa_habilitado')
