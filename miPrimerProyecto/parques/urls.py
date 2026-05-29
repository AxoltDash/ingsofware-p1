from django.urls import path

from . import views

urlpatterns = [
    path('api/marcadores/', views.api_marcadores, name='api_marcadores'),

    # Panel de administrador — parques
    path('admin/', views.admin_parques, name='admin_parques'),
    path('admin/crear/', views.crear_parque, name='crear_parque'),
    path('admin/<int:parque_id>/editar/', views.editar_parque, name='editar_parque'),
    path('admin/<int:parque_id>/desactivar/', views.eliminar_parque, name='eliminar_parque'),

    # Panel de administrador — cabañas
    path('admin/<int:parque_id>/cabanas/', views.admin_cabanas, name='admin_cabanas'),
    path('admin/<int:parque_id>/cabanas/crear/', views.crear_cabana, name='crear_cabana'),
    path('admin/<int:parque_id>/disponibilidad/', views.gestionar_disponibilidad, name='gestionar_disponibilidad'),
    path('admin/cabanas/<int:cabana_id>/editar/', views.editar_cabana, name='editar_cabana'),
    path('admin/cabanas/<int:cabana_id>/desactivar/', views.desactivar_cabana, name='desactivar_cabana'),
]
