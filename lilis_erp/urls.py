"""
URL configuration for lilis_erp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views # Importamos las vistas del proyecto
from apps.account.views import module_gate_view  # 🔹 Importa la vista del portón

from django.contrib import admin
from django.urls import path, include
from . import views
from apps.account.views import module_gate_view

urlpatterns = [
    # Raíz → dashboard (solo admin lo verá; no admin será redirigido en la vista)
    path("", views.dashboard_page, name="dashboard"),

    path("admin/", admin.site.urls),

    # Auth
    path("", include("apps.account.urls")),

    # Módulos (namespaced para que {% url 'suppliers:list' %} etc. funcione)
    path("productos/", include(("apps.products.urls", "products"), namespace="products")),
    path("users/", include("apps.users.urls")),
    path("proveedores/", include(("apps.suppliers.urls", "suppliers"), namespace="suppliers")),
    path("transacciones/", include(("apps.transactional.urls", "transactional"), namespace="transactional")),

    # Portón (lo dejamos tal cual)
    path("modulos/<slug:app_slug>/entrar/", module_gate_view, name="module_gate"),
]

