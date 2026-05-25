from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('bosques/', views.bosques, name='bosques'),
    path('siames/', views.siames, name='siames'),
]
