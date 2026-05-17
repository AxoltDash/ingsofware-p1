from django.contrib import admin
from .models import Parque


@admin.register(Parque)
class ParqueAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'tiene_cabanas', 'activo')
    list_filter = ('tiene_cabanas', 'activo')
    search_fields = ('nombre', 'direccion')
