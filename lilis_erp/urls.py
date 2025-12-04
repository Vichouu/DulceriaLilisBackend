from django.contrib import admin
from django.urls import path, include
from . import views
from apps.account.views import module_gate_view

# ==========================
# JWT
# ==========================
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# ==========================
# Swagger / Redoc
# ==========================
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions


schema_view = get_schema_view(
    openapi.Info(
        title="Dulcería Lilis ERP - API REST",
        default_version="v1",
        description=(
            "Documentación oficial del sistema ERP con API REST.\n"
            "Incluye módulos de Usuarios, Productos, Proveedores y Transacciones."
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


# ==========================
# URLS PRINCIPALES
# ==========================
urlpatterns = [

    # Dashboard principal
    path("", views.dashboard_page, name="dashboard"),

    # Admin Django
    path("admin/", admin.site.urls),

    # Autenticación (login, logout, register)
    path("", include("apps.account.urls")),

    # Módulos internos del ERP
    path(
        "productos/",
        include(("apps.products.urls", "products"), namespace="products")
    ),
    path("users/", include("apps.users.urls")),
    path(
        "proveedores/",
        include(("apps.suppliers.urls", "suppliers"), namespace="suppliers")
    ),
    path(
        "transacciones/",
        include(("apps.transactional.urls", "transactional"), namespace="transactional")
    ),

    # Acceso por módulo (portón)
    path("modulos/<slug:app_slug>/entrar/", module_gate_view, name="module_gate"),

    # API REST CRUD
    path("api/", include("apps.api.urls")),

    # JWT Authentication
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]


# ==========================
# Documentación Swagger / ReDoc
# ==========================
urlpatterns += [
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="redoc-ui"),
]
