# apps/users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('gestion/', views.gestion_usuarios, name='gestion_usuarios'),
    path('crear/', views.crear_usuario, name='crear_usuario'),
    path('editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),
    path('eliminar/<int:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),

    # nuevos
    path('desactivar/<int:user_id>/', views.desactivar_usuario, name='desactivar_usuario'),
    path('reactivar/<int:user_id>/', views.reactivar_usuario, name='reactivar_usuario'),
    path('reiniciar_clave/<int:user_id>/', views.reiniciar_clave, name='reiniciar_clave'),
    path('bloquear/<int:user_id>/', views.bloquear_usuario, name='bloquear_usuario'),
    path('desbloquear/<int:user_id>/', views.desbloquear_usuario, name='desbloquear_usuario'),
]