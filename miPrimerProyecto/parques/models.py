from django.db import models


class Parque(models.Model):
    nombre            = models.CharField(max_length=200)
    direccion         = models.CharField(max_length=300)
    servicios         = models.JSONField(default=list)
    horario           = models.CharField(max_length=100)
    latitud           = models.DecimalField(max_digits=9, decimal_places=6)
    longitud          = models.DecimalField(max_digits=9, decimal_places=6)
    tiene_cabanas     = models.BooleanField(default=False)
    capacidad_cabanas = models.PositiveIntegerField(default=0)
    capacidad_camping = models.PositiveIntegerField(default=0)
    activo            = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'parque'
