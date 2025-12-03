# apps/account/admin.py
from django.contrib import admin

# Intentamos importar Perfil; si no existe todavía, evitamos que el admin se caiga.
try:
    from .models import Perfil
except Exception:
    Perfil = None

# Si el modelo Perfil existe, lo registramos normalmente
if Perfil:
    @admin.register(Perfil)
    class PerfilAdmin(admin.ModelAdmin):
        list_display = ("usuario", "cargo", "avatar_url")
        search_fields = ("usuario__username", "usuario__email", "cargo")
