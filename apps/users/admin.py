from django.contrib import admin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "telefono", "is_staff", "activo", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active", "activo")
    search_fields = ("username", "email", "first_name", "last_name", "telefono")
    ordering = ("username",)
    fieldsets = (
        ("Credenciales", {"fields": ("username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "email", "telefono", "area")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Seguridad", {"fields": ("mfa_habilitado",)}),
        ("Estado", {"fields": ("activo",)}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("last_login", "date_joined")