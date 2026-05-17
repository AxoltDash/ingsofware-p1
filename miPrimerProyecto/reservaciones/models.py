from django.db import models


class TipoVisita(models.TextChoices):
    CABANA  = 'CABANA',  'Cabaña'
    CAMPING = 'CAMPING', 'Camping'


class EstadoReservacion(models.TextChoices):
    ACTIVA     = 'ACTIVA',     'Activa'
    CANCELADA  = 'CANCELADA',  'Cancelada'
    FINALIZADA = 'FINALIZADA', 'Finalizada'


class Reservacion(models.Model):
    cliente         = models.ForeignKey(
                          'usuarios.Cliente',
                          on_delete=models.PROTECT,
                          related_name='reservaciones'
                      )
    parque          = models.ForeignKey(
                          'parques.Parque',
                          on_delete=models.PROTECT,
                          related_name='reservaciones'
                      )
    fecha_inicio    = models.DateField()
    fecha_termino   = models.DateField()
    numero_personas = models.PositiveIntegerField()
    tipo_visita     = models.CharField(max_length=10, choices=TipoVisita.choices)
    estado          = models.CharField(
                          max_length=12,
                          choices=EstadoReservacion.choices,
                          default=EstadoReservacion.ACTIVA
                      )
    fecha_creacion  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'reservación'
