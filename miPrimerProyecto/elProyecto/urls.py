from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),   
    path('siames/', views.siames, name='siames'),
    path('creepyNuts/', views.creepyNuts, name='creepyNuts'),
    path("login/", views.login_view, name="login"),
    path("registro/", views.register_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),
]