# ============================
#   IMPORTS
# ============================
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import models   # necesario para SUM y aggregate

# PERMISSIONS
from rest_framework.permissions import AllowAny
from .permissions import IsAdminRole

# MODELOS
from apps.users.models import Usuario
from apps.products.models import Producto
from apps.suppliers.models import Proveedor
from apps.transactional.models import MovimientoInventario as Movimiento

# SERIALIZERS
from .serializers import (
    UsuarioSerializer,
    ProductoSerializer,
    ProveedorSerializer,
    MovimientoInventarioSerializer,
)

# ============================
#   API ROOT (para /api/)
# ============================
@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    """
    Página inicial de la API para que /api/ no devuelva 404.
    Retorna un índice con los endpoints disponibles.
    """
    base = request.build_absolute_uri()

    return Response({
        "message": "Bienvenido a la API REST de Dulcería Lilis",
        "endpoints": {
            "usuarios": {
                "listar / crear": base + "usuarios/",
                "detalle": base + "usuarios/<id>/",
            },
            "productos": {
                "listar / crear": base + "productos/",
                "detalle": base + "productos/<id>/",
            },
            "proveedores": {
                "listar / crear": base + "proveedores/",
                "detalle": base + "proveedores/<id>/",
            },
            "transacciones": {
                "listar / crear": base + "transacciones/",
                "detalle": base + "transacciones/<id>/",
            },
            "stock": base + "stock/<id>/",
            "auth": {
                "token_obtain": request.build_absolute_uri("/api/token/"),
                "token_refresh": request.build_absolute_uri("/api/token/refresh/"),
            },
            "documentación": {
                "swagger": request.build_absolute_uri("/swagger/"),
                "redoc": request.build_absolute_uri("/redoc/"),
            }
        }
    })


# ============================
#   USUARIOS
# ============================
@api_view(["GET", "POST"])
@permission_classes([IsAdminRole])
def usuarios_list_create(request):
    if request.method == "GET":
        usuarios = Usuario.objects.all()
        serializer = UsuarioSerializer(usuarios, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = UsuarioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def usuarios_detail(request, pk):
    try:
        usuario = Usuario.objects.get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado."}, status=404)

    if request.method == "GET":
        return Response(UsuarioSerializer(usuario).data)

    if request.method in ["PUT", "PATCH"]:
        serializer = UsuarioSerializer(
            usuario, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    if request.method == "DELETE":
        usuario.delete()
        return Response(status=204)


# ============================
#   PRODUCTOS
# ============================
@api_view(["GET", "POST"])
@permission_classes([IsAdminRole])
def productos_list_create(request):
    if request.method == "GET":
        productos = Producto.objects.all()
        serializer = ProductoSerializer(productos, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = ProductoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def productos_detail(request, pk):
    try:
        producto = Producto.objects.get(pk=pk)
    except Producto.DoesNotExist:
        return Response({"detail": "Producto no encontrado."}, status=404)

    if request.method == "GET":
        return Response(ProductoSerializer(producto).data)

    if request.method in ["PUT", "PATCH"]:
        serializer = ProductoSerializer(
            producto, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    if request.method == "DELETE":
        producto.delete()
        return Response(status=204)


# ============================
#   PROVEEDORES
# ============================
@api_view(["GET", "POST"])
@permission_classes([IsAdminRole])
def proveedores_list_create(request):
    if request.method == "GET":
        proveedores = Proveedor.objects.all()
        serializer = ProveedorSerializer(proveedores, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = ProveedorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def proveedores_detail(request, pk):
    try:
        proveedor = Proveedor.objects.get(pk=pk)
    except Proveedor.DoesNotExist:
        return Response({"detail": "Proveedor no encontrado."}, status=404)

    if request.method == "GET":
        return Response(ProveedorSerializer(proveedor).data)

    if request.method in ["PUT", "PATCH"]:
        serializer = ProveedorSerializer(
            proveedor, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    if request.method == "DELETE":
        proveedor.delete()
        return Response(status=204)


# ============================
#   TRANSACCIONES
# ============================
@api_view(["GET", "POST"])
@permission_classes([IsAdminRole])
def transacciones_list_create(request):
    if request.method == "GET":
        movs = Movimiento.objects.all()
        serializer = MovimientoInventarioSerializer(movs, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = MovimientoInventarioSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(creado_por=request.user)
            instance.aplicar_a_stock()
            return Response(MovimientoInventarioSerializer(instance).data, status=201)
        return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def transacciones_detail(request, pk):
    try:
        mov = Movimiento.objects.get(pk=pk)
    except Movimiento.DoesNotExist:
        return Response({"detail": "Movimiento no encontrado."}, status=404)

    if request.method == "GET":
        return Response(MovimientoInventarioSerializer(mov).data)

    if request.method in ["PUT", "PATCH"]:
        serializer = MovimientoInventarioSerializer(
            mov, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            instance = serializer.save()
            return Response(MovimientoInventarioSerializer(instance).data)
        return Response(serializer.errors, status=400)

    if request.method == "DELETE":
        mov.delete()
        return Response(status=204)


# ============================
#   ENDPOINT: STOCK REAL
# ============================
@api_view(["GET"])
@permission_classes([IsAdminRole])
def stock_producto(request, pk):
    try:
        producto = Producto.objects.get(pk=pk)
    except Producto.DoesNotExist:
        return Response({"detail": "Producto no encontrado."}, status=404)

    entradas = (
        Movimiento.objects.filter(producto=producto, tipo="INGRESO")
        .aggregate(total=models.Sum("cantidad"))["total"]
        or 0
    )

    salidas = (
        Movimiento.objects.filter(producto=producto, tipo="SALIDA")
        .aggregate(total=models.Sum("cantidad"))["total"]
        or 0
    )

    stock_actual = entradas - salidas

    return Response({
        "producto_id": producto.id,
        "producto": producto.nombre,
        "stock": stock_actual
    })
