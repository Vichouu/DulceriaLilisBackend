from django.urls import path
from . import views

app_name = 'transactional'

urlpatterns = [
    path('', views.gestion_transacciones, name='list'),
    path('crear/', views.crear_transaccion, name='crear'),
    path('editar/<int:mov_id>/', views.editar_transaccion, name='editar'),
    path('eliminar/<int:mov_id>/', views.eliminar_transaccion, name='eliminar'),
]