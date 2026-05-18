from django.db import models


class Parque(models.Model):
    nombre            = models.CharField(max_length=200)
    direccion         = models.CharField(max_length=300)
    servicios         = models.JSONField(default=list)
    horario           = models.CharField(max_length=100)
    latitud           = models.DecimalField(max_digits=9, decimal_places=6)
    longitud          = models.DecimalField(max_digits=9, decimal_places=6)
    tiene_cabanas     = models.BooleanField(default=False)
    capacidad_camping = models.PositiveIntegerField(default=0)
    activo            = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'parque'


class Cabana(models.Model):
    """
    Cabaña individual con identidad propia dentro de un parque.
    Una reservación CABANA ocupa exactamente una instancia de este modelo.
    Nunca dos reservaciones activas apuntan a la misma Cabana en fechas solapadas.
    """
    parque    = models.ForeignKey(
                    Parque,
                    on_delete=models.CASCADE,
                    related_name='cabanas'
                )
    nombre    = models.CharField(max_length=100)
    capacidad = models.PositiveIntegerField()
    activo    = models.BooleanField(default=True)

    def esta_disponible(self, fecha_inicio, fecha_termino):
        from reservaciones.models import Reservacion, EstadoReservacion
        return not Reservacion.objects.filter(
            cabana=self,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,
            fecha_termino__gt=fecha_inicio
        ).exists()

    def __str__(self):
        return f"{self.parque.nombre} — {self.nombre} ({self.capacidad} personas)"

    class Meta:
        verbose_name = 'cabaña'
        unique_together = ('parque', 'nombre')


class Marcador(models.Model):
    parque   = models.OneToOneField(Parque, on_delete=models.CASCADE, related_name='marcador')
    latitud  = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        verbose_name = 'marcador'
