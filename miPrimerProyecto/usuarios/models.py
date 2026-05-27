import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager  # incluye password con hash+sal, is_active, date_joined, etc.
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    """Manager personalizado que usa email en lugar de username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        email = self.normalize_email(email)  # normaliza dominio a minúsculas
        user = self.model(email=email, **extra_fields)
        user.set_password(password)          # aplica el hasher configurado (Argon2)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # createsuperuser llama a este método; sin él Django busca 'username' y falla
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    username = None  # eliminamos username el identificador de login será el email
    email = models.EmailField(unique=True)  # unique=True impide dos cuentas con el mismo correo

    objects = UsuarioManager()  # reemplaza el UserManager por defecto que requería username

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


class PasswordResetToken(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,     # si se elimina el usuario, sus tokens desaparecen
        related_name='reset_tokens'
    )
    token  = models.CharField(max_length=64, unique=True)  # 43 chars: secrets.token_urlsafe(32)
    expira = models.DateTimeField()                         # timestamp absoluto de vencimiento
    usado  = models.BooleanField(default=False)             # se marca True al usarse, impide reutilización

    @classmethod
    def crear_para(cls, usuario):
        cls.objects.filter(usuario=usuario, usado=False).update(usado=True)  # invalida tokens anteriores del mismo usuario
        return cls.objects.create(
            usuario=usuario,
            token=secrets.token_urlsafe(32),              # [OWASP 2.6] token criptográfico seguro de 32 bytes
            expira=timezone.now() + timedelta(minutes=30) # válido 30 minutos desde la solicitud
        )

    def es_valido(self):
        return not self.usado and self.expira > timezone.now()  # doble barrera: no usado Y no vencido

    class Meta:
        verbose_name = 'token de recuperación'
