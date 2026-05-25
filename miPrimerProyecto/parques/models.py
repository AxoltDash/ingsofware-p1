from django.db import models


class Parque(models.Model):
    nombre            = models.CharField(max_length=200)
    direccion         = models.CharField(max_length=300)
    servicios         = models.JSONField(default=list)          # lista de strings, ej. ["baños", "estacionamiento"]
    horario           = models.CharField(max_length=100)
    latitud           = models.DecimalField(max_digits=9, decimal_places=6)   # DecimalField es más preciso que FloatField para coordenadas GPS
    longitud          = models.DecimalField(max_digits=9, decimal_places=6)
    tiene_cabanas     = models.BooleanField(default=False)      # RF-04.4: indica si el parque ofrece cabañas
    capacidad_camping = models.PositiveIntegerField(default=0)  # personas máx compartiendo la zona de camping; PositiveIntegerField rechaza valores negativos en BD
    activo            = models.BooleanField(default=True)       # soft delete: se desactiva en lugar de borrar para conservar historial de reservaciones

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
                    on_delete=models.CASCADE,   # si se elimina el parque, sus cabañas desaparecen también (sin parque no existe cabaña)
                    related_name='cabanas'       # permite parque.cabanas.all()
                )
    nombre    = models.CharField(max_length=100)      # identificador legible, ej. "Cabaña 1", "Suite Familiar"
    capacidad = models.PositiveIntegerField()          # sin default: siempre debe definirse; BD rechaza 0 y negativos (OWASP 2.1)
    activo    = models.BooleanField(default=True)     # soft delete independiente del parque: se puede desactivar una cabaña sin tocar las demás

    def esta_disponible(self, fecha_inicio, fecha_termino):
        from reservaciones.models import Reservacion, EstadoReservacion  # importación local para evitar circular import: parques ↔ reservaciones
        return not Reservacion.objects.filter(
            cabana=self,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,   # hay solapamiento si la reservación existente empieza ANTES de que termine la nueva
            fecha_termino__gt=fecha_inicio    # y termina DESPUÉS de que empiece la nueva
        ).exists()

    def __str__(self):
        return f"{self.parque.nombre} — {self.nombre} ({self.capacidad} personas)"

    class Meta:
        verbose_name = 'cabaña'
        unique_together = ('parque', 'nombre')  # no puede haber dos cabañas con el mismo nombre en el mismo parque


class Marcador(models.Model):
    parque   = models.OneToOneField(Parque, on_delete=models.CASCADE, related_name='marcador')  # OneToOne: cada parque tiene exactamente un pin en el mapa
    latitud  = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        verbose_name = 'marcador'
