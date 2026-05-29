from django.contrib import admin
from django.urls import path, include

# [OWASP 2.7] Páginas de error personalizadas — sin exponer stack traces al usuario
handler404 = 'miPrimerProyecto.views.error_404'
handler500 = 'miPrimerProyecto.views.error_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('usuarios.urls')),         # login, logout, registro, recuperación
    path('reservaciones/', include('reservaciones.urls')),  # mis reservaciones, cancelar, admin
    path('parques/', include('parques.urls')),        # api de marcadores para el mapa
    path('', include('elProyecto.urls')),            # home, bosques y otras vistas del sitio
]
