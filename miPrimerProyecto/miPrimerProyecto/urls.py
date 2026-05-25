from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('usuarios.urls')),  # login, logout, registro, recuperación de contraseña
    path('', include('elProyecto.urls')),     # home, bosques y otras vistas del sitio
]
