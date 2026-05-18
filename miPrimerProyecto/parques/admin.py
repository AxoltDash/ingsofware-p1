from django.contrib import admin
from .models import Parque, Cabana, Marcador


class CabanaInline(admin.TabularInline):
    model = Cabana
    extra = 1
    fields = ('nombre', 'capacidad', 'activo')


@admin.register(Parque)
class ParqueAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'tiene_cabanas', 'capacidad_camping', 'activo')
    list_filter = ('tiene_cabanas', 'activo')
    search_fields = ('nombre', 'direccion')
    inlines = [CabanaInline]


@admin.register(Cabana)
class CabanaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'parque', 'capacidad', 'activo')
    list_filter = ('activo', 'parque')
    search_fields = ('nombre', 'parque__nombre')


@admin.register(Marcador)
class MarcadorAdmin(admin.ModelAdmin):
    list_display = ('parque', 'latitud', 'longitud')
