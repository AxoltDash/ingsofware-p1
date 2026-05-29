from django.urls import path

from . import views

urlpatterns = [
    path('mis-reservaciones/', views.mis_reservaciones, name='mis_reservaciones'),
    path('cancelar/<int:reservacion_id>/', views.cancelar_reservacion, name='cancelar_reservacion'),
    path('todas/', views.todas_reservaciones, name='todas_reservaciones'),
    path('reservar/<int:parque_id>/', views.reservar_paso1, name='reservar_paso1'),
    path('reservar/<int:parque_id>/cabana/', views.seleccionar_cabana, name='seleccionar_cabana'),
]
