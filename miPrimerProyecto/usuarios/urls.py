from django.urls import path

from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('recuperar/', views.solicitar_recuperacion, name='recuperar_contrasenia'),
    path('restablecer/<str:token>/', views.restablecer_contrasenia, name='restablecer_contrasenia'),
]
