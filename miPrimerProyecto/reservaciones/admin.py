from django.contrib import admin
from .models import Reservacion


@admin.register(Reservacion)
class ReservacionAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'parque', 'fecha_inicio', 'fecha_termino', 'tipo_visita', 'estado')
    list_filter = ('tipo_visita', 'estado')
    search_fields = ('cliente__email', 'parque__nombre')
