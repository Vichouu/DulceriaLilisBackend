# apps/api/serializers.py
from rest_framework import serializers
from apps.users.models import Usuario
from apps.products.models import Producto
from apps.suppliers.models import Proveedor
from apps.transactional.models import MovimientoInventario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = "__all__"  # si la profe pide algo más acotado, luego lo afinamos


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = "__all__"


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = "__all__"
