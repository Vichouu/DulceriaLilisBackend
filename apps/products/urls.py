from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list_view, name='list'),
    path('search/', views.search_products, name='search'),
    path('crear/', views.crear_producto, name='crear'),
    path('editar/<int:prod_id>/', views.editar_producto, name='editar'),
    path('eliminar/<int:prod_id>/', views.eliminar_producto, name='eliminar'),
]