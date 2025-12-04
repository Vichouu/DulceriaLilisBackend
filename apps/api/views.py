from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import Usuario
from apps.products.models import Producto
from apps.suppliers.models import Proveedor
from apps.transactional.models import MovimientoInventario

from .serializers import (
    UsuarioSerializer,
    ProductoSerializer,
    ProveedorSerializer,
    MovimientoInventarioSerializer,
)
from .permissions import IsAdminRole


# ========= USUARIOS =========

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
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def usuarios_detail(request, pk):
    try:
        usuario = Usuario.objects.get(pk=pk)
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = UsuarioSerializer(usuario)
        return Response(serializer.data)

    if request.method in ["PUT", "PATCH"]:
        partial = (request.method == "PATCH")
        serializer = UsuarioSerializer(usuario, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        usuario.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ========= PRODUCTOS =========

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
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def productos_detail(request, pk):
    try:
        producto = Producto.objects.get(pk=pk)
    except Producto.DoesNotExist:
        return Response({"detail": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ProductoSerializer(producto)
        return Response(serializer.data)

    if request.method in ["PUT", "PATCH"]:
        partial = (request.method == "PATCH")
        serializer = ProductoSerializer(producto, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        producto.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ========= PROVEEDORES =========

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
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def proveedores_detail(request, pk):
    try:
        proveedor = Proveedor.objects.get(pk=pk)
    except Proveedor.DoesNotExist:
        return Response({"detail": "Proveedor no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ProveedorSerializer(proveedor)
        return Response(serializer.data)

    if request.method in ["PUT", "PATCH"]:
        partial = (request.method == "PATCH")
        serializer = ProveedorSerializer(proveedor, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        proveedor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ========= TRANSACCIONES (MOVIMIENTOS DE INVENTARIO) =========

@api_view(["GET", "POST"])
@permission_classes([IsAdminRole])
def transacciones_list_create(request):
    if request.method == "GET":
        movs = MovimientoInventario.objects.all()
        serializer = MovimientoInventarioSerializer(movs, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = MovimientoInventarioSerializer(data=request.data)
        if serializer.is_valid():
            # El modelo ya tiene lógica para ajustar stock en save()
            instance = serializer.save(creado_por=request.user)
            return Response(MovimientoInventarioSerializer(instance).data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminRole])
def transacciones_detail(request, pk):
    try:
        mov = MovimientoInventario.objects.get(pk=pk)
    except MovimientoInventario.DoesNotExist:
        return Response({"detail": "Movimiento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = MovimientoInventarioSerializer(mov)
        return Response(serializer.data)

    if request.method in ["PUT", "PATCH"]:
        partial = (request.method == "PATCH")
        serializer = MovimientoInventarioSerializer(mov, data=request.data, partial=partial)
        if serializer.is_valid():
            instance = serializer.save()
            return Response(MovimientoInventarioSerializer(instance).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        mov.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
