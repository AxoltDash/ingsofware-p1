from django.contrib.auth.models import AbstractUser  # incluye password con hash+sal, is_active, date_joined, etc.
from django.db import models


class Usuario(AbstractUser):
    username = None  # eliminamos username el identificador de login será el email
    email = models.EmailField(unique=True)  # unique=True impide dos cuentas con el mismo correo

    USERNAME_FIELD = 'email'   # Django usará email en lugar de username al autenticar
    REQUIRED_FIELDS = []       # vacío porque email ya está en USERNAME_FIELD evita pedirlo dos veces en createsuperuser

    class Meta:
        verbose_name = 'usuario'


class Cliente(Usuario):
    # hereda todo de Usuario y crea su propia tabla en BD (multi-table inheritance)
    # permite distinguir rol en consultas: Cliente.objects.all() y Administrador.objects.all()
    class Meta:
        verbose_name = 'cliente'


class Administrador(Usuario):
    # misma estrategia que Cliente; cada rol tiene su propia fila en la BD
    class Meta:
        verbose_name = 'administrador'
