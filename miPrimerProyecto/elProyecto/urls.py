from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('bosques/', views.bosques, name='bosques'),
    path('registro/', views.registro, name='registro'),
    path('reservaciones/', views.reservaciones, name='reservaciones'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
