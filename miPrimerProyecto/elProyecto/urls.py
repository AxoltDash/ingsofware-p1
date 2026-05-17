from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('', views.home, name='home'),   
    path('siames/', views.siames, name='siames'),
    path('creepyNuts/', views.creepyNuts, name='creepyNuts'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('bosques/', views.bosques, name='bosques'),
]