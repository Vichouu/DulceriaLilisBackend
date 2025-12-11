from django.urls import path
from . import views

urlpatterns = [
    # 🌐 API Root (para que /api/ ya no dé 404)
    path("", views.api_root, name="api_root"),

    # Usuarios
    path("usuarios/", views.usuarios_list_create, name="api_usuarios_list"),
    path("usuarios/<int:pk>/", views.usuarios_detail, name="api_usuarios_detail"),

    # Productos
    path("productos/", views.productos_list_create, name="api_productos_list"),
    path("productos/<int:pk>/", views.productos_detail, name="api_productos_detail"),

    # Proveedores
    path("proveedores/", views.proveedores_list_create, name="api_proveedores_list"),
    path("proveedores/<int:pk>/", views.proveedores_detail, name="api_proveedores_detail"),

    # Transacciones
    path("transacciones/", views.transacciones_list_create, name="api_transacciones_list"),
    path("transacciones/<int:pk>/", views.transacciones_detail, name="api_transacciones_detail"),

    # Stock real por producto
    path("stock/<int:pk>/", views.stock_producto, name="api_stock_producto"),
]
