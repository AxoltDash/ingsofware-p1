from django.db import models
from django.contrib.auth.models import User

class Parque(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300)
    servicios = models.TextField(help_text="Servicios separados por coma")
    horario = models.CharField(max_length=100)
    tiene_cabana = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre