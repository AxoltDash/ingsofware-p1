from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'usuario'


class Cliente(Usuario):
    class Meta:
        verbose_name = 'cliente'


class Administrador(Usuario):
    class Meta:
        verbose_name = 'administrador'
