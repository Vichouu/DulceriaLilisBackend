from django.urls import path
from . import views

app_name = "suppliers"

urlpatterns = [
    path("", views.supplier_list_view, name="list"),
    path("create/", views.create_supplier, name="create"),
    path("editar/<int:supplier_id>/", views.editar_proveedor, name="edit"),
    path("eliminar/<int:supplier_id>/", views.eliminar_proveedor, name="delete"),
    path("relations/create/", views.create_relation, name="relations_create"),
    path("search/", views.search_suppliers, name="search"),
    path("relations/search/", views.relations_search, name="relations_search"),
    path("relations/export/", views.relations_export, name="relations_export"),
    path('desactivar/<int:supplier_id>/', views.desactivar_proveedor, name='desactivar_proveedor'),
    path('reactivar/<int:supplier_id>/', views.reactivar_proveedor, name='reactivar_proveedor'),
    path('relacion/eliminar/<int:relation_id>/', views.eliminar_relacion, name='delete_relation'),
]