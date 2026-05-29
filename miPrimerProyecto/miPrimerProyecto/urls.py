from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('usuarios.urls')),         # login, logout, registro, recuperación
    path('reservaciones/', include('reservaciones.urls')),  # mis reservaciones, cancelar, admin
    path('parques/', include('parques.urls')),        # api de marcadores para el mapa
    path('', include('elProyecto.urls')),            # home, bosques y otras vistas del sitio
]
