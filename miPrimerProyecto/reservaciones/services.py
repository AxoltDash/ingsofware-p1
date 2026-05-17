from datetime import date, timedelta
from django.db import models, transaction

from .models import Reservacion, TipoVisita, EstadoReservacion


class GestorReservaciones:

    @staticmethod
    def verificar_periodo_festival(fecha_inicio, fecha_termino):
        """RN-01: solo junio-agosto"""
        meses_validos = {6, 7, 8}
        if fecha_inicio.month not in meses_validos:
            raise ValueError("La fecha de inicio debe ser entre junio y agosto.")
        if fecha_termino.month not in meses_validos:
            raise ValueError("La fecha de término debe ser entre junio y agosto.")

    @staticmethod
    def verificar_no_martes(fecha_inicio, fecha_termino):
        """RN-02: ningún día del rango puede ser martes"""
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_termino:
            if fecha_actual.weekday() == 1:
                raise ValueError("Las reservaciones no pueden incluir días martes.")
            fecha_actual += timedelta(days=1)

    @staticmethod
    def verificar_traslape(parque, fecha_inicio, fecha_termino, tipo_visita,
                           excluir_id=None):
        """RF-03.8: no reservaciones traslapadas"""
        qs = Reservacion.objects.filter(
            parque=parque,
            tipo_visita=tipo_visita,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,
            fecha_termino__gt=fecha_inicio,
        )
        if excluir_id:
            qs = qs.exclude(id=excluir_id)
        return qs.exists()

    @staticmethod
    def verificar_disponibilidad(parque, fecha_inicio, fecha_termino,
                                 tipo_visita, numero_personas):
        """RN-07, RN-08: respetar capacidad máxima"""
        ocupacion = Reservacion.objects.filter(
            parque=parque,
            tipo_visita=tipo_visita,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,
            fecha_termino__gt=fecha_inicio,
        ).aggregate(total=models.Sum('numero_personas'))['total'] or 0

        capacidad = (
            parque.capacidad_cabanas
            if tipo_visita == TipoVisita.CABANA
            else parque.capacidad_camping
        )

        if ocupacion + numero_personas > capacidad:
            raise ValueError(
                f"No hay disponibilidad suficiente. "
                f"Disponible: {capacidad - ocupacion} lugares."
            )

    @classmethod
    def crear_reservacion(cls, cliente, parque, fecha_inicio,
                          fecha_termino, numero_personas, tipo_visita):
        """CU-03: crea reservación validando todas las reglas de negocio."""
        with transaction.atomic():
            cls.verificar_periodo_festival(fecha_inicio, fecha_termino)
            cls.verificar_no_martes(fecha_inicio, fecha_termino)
            cls.verificar_disponibilidad(
                parque, fecha_inicio, fecha_termino, tipo_visita, numero_personas
            )
            if cls.verificar_traslape(parque, fecha_inicio, fecha_termino, tipo_visita):
                raise ValueError("Ya existe una reservación para ese parque y fechas.")

            return Reservacion.objects.create(
                cliente=cliente,
                parque=parque,
                fecha_inicio=fecha_inicio,
                fecha_termino=fecha_termino,
                numero_personas=numero_personas,
                tipo_visita=tipo_visita,
            )
