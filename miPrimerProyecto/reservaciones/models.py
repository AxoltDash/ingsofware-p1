from django.core.exceptions import ValidationError
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
    cabana          = models.ForeignKey(
                          'parques.Cabana',
                          on_delete=models.PROTECT,
                          related_name='reservaciones',
                          null=True,
                          blank=True
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

    def clean(self):
        """[OWASP 2.1] Invariante: CABANA requiere cabana, CAMPING no debe tenerla."""
        if self.tipo_visita == TipoVisita.CABANA and self.cabana is None:
            raise ValidationError("Una reservación de cabaña requiere especificar la cabaña.")
        if self.tipo_visita == TipoVisita.CAMPING and self.cabana is not None:
            raise ValidationError("Una reservación de camping no debe tener cabaña asignada.")
        if self.cabana and self.cabana.parque_id != self.parque_id:
            raise ValidationError("La cabaña no pertenece al parque seleccionado.")

    class Meta:
        verbose_name = 'reservación'
