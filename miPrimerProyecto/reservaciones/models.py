from django.core.exceptions import ValidationError
from django.db import models


class TipoVisita(models.TextChoices):
    # TextChoices para que el ORM rechace cualquier valor fuera de esta lista
    CABANA  = 'CABANA',  'Cabaña'
    CAMPING = 'CAMPING', 'Camping'


class EstadoReservacion(models.TextChoices):
    ACTIVA     = 'ACTIVA',     'Activa'
    CANCELADA  = 'CANCELADA',  'Cancelada'
    FINALIZADA = 'FINALIZADA', 'Finalizada'


class Reservacion(models.Model):
    cliente         = models.ForeignKey(
                          'usuarios.Cliente',
                          on_delete=models.PROTECT,    # PROTECT impide borrar un cliente que tenga reservaciones registradas
                          related_name='reservaciones'
                      )
    parque          = models.ForeignKey(
                          'parques.Parque',
                          on_delete=models.PROTECT,    # ídem: no se puede eliminar un parque con historial de reservaciones
                          related_name='reservaciones'
                      )
    cabana          = models.ForeignKey(
                          'parques.Cabana',
                          on_delete=models.PROTECT,    # PROTECT: no borrar una cabaña si tiene reservaciones asociadas
                          related_name='reservaciones',
                          null=True,   # None cuando tipo_visita=CAMPING; obligatorio solo para CABANA
                          blank=True   # permite el campo vacío en formularios Django
                      )
    fecha_inicio    = models.DateField()
    fecha_termino   = models.DateField()
    numero_personas = models.PositiveIntegerField()     # rechaza 0 y negativos 
    tipo_visita     = models.CharField(
                          max_length=10,
                          choices=TipoVisita.choices   # el ORM valida que el valor sea CABANA o CAMPING
                      )
    estado          = models.CharField(
                          max_length=12,
                          choices=EstadoReservacion.choices, # el ORM valida que el valor sea CABANA o CAMPING
                          default=EstadoReservacion.ACTIVA  # toda reservación se crea con estado de activa
                      )
    fecha_creacion  = models.DateTimeField(auto_now_add=True)  # la BD registra el momento exacto de creación; no es editable

    def clean(self):
        """Invariante: CABANA requiere cabana, CAMPING no debe tenerla."""
        # segunda barrera de validación: GestorReservaciones ya valida esto, clean() lo refuerza a nivel de modelo
        if self.tipo_visita == TipoVisita.CABANA and self.cabana is None:
            raise ValidationError("Una reservación de cabaña requiere especificar la cabaña.")
        if self.tipo_visita == TipoVisita.CAMPING and self.cabana is not None:
            raise ValidationError("Una reservación de camping no debe tener cabaña asignada.")
        if self.cabana and self.cabana.parque_id != self.parque_id:  # _id evita una query extra a la BD
            raise ValidationError("La cabaña no pertenece al parque seleccionado.")

    class Meta:
        verbose_name = 'reservación'
