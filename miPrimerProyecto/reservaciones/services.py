from datetime import timedelta
from django.db import transaction
from django.db.models import Sum

from .models import Reservacion, TipoVisita, EstadoReservacion


class GestorReservaciones:

    @staticmethod
    def verificar_periodo_festival(fecha_inicio, fecha_termino):
        """RN-01: solo junio-agosto [OWASP 2.1]"""
        meses_validos = {6, 7, 8}
        if fecha_inicio.month not in meses_validos or fecha_termino.month not in meses_validos:
            raise ValueError("Las reservaciones solo son válidas de junio a agosto.")

    @staticmethod
    def verificar_no_martes(fecha_inicio, fecha_termino):
        """RN-02: ningún día del rango puede ser martes [OWASP 2.1]"""
        fecha = fecha_inicio
        while fecha <= fecha_termino:
            if fecha.weekday() == 1:
                raise ValueError("Las reservaciones no pueden incluir días martes.")
            fecha += timedelta(days=1)

    @staticmethod
    def cabanas_disponibles(parque, fecha_inicio, fecha_termino, numero_personas):
        """
        Devuelve cabañas del parque que cumplen ambas condiciones:
          1. Capacidad individual >= numero_personas
          2. Sin reservación ACTIVA solapada en el rango de fechas
        Usado para mostrar opciones al cliente antes de reservar. [OWASP 2.1, 2.11]
        """
        from parques.models import Cabana
        cabanas_ocupadas_ids = Reservacion.objects.filter(
            parque=parque,
            tipo_visita=TipoVisita.CABANA,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,
            fecha_termino__gt=fecha_inicio
        ).values_list('cabana_id', flat=True)

        return Cabana.objects.filter(
            parque=parque,
            activo=True,
            capacidad__gte=numero_personas
        ).exclude(id__in=cabanas_ocupadas_ids)

    @staticmethod
    def verificar_disponibilidad_cabana(cabana, fecha_inicio, fecha_termino, numero_personas):
        """
        Verifica que una cabaña específica esté libre y tenga capacidad suficiente.
        select_for_update() evita race conditions (RNF-05). [OWASP 2.1, 2.11]
        """
        if numero_personas > cabana.capacidad:
            raise ValueError(
                f"El grupo ({numero_personas} personas) excede la capacidad "
                f"de {cabana.nombre} ({cabana.capacidad} personas máx)."
            )
        solapada = Reservacion.objects.select_for_update().filter(
            cabana=cabana,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,
            fecha_termino__gt=fecha_inicio
        ).exists()
        if solapada:
            raise ValueError(
                f"{cabana.nombre} ya está reservada para esas fechas. "
                "Por favor selecciona otra cabaña disponible."
            )

    @staticmethod
    def verificar_disponibilidad_camping(parque, fecha_inicio, fecha_termino, numero_personas):
        """
        Camping: acumulable. Varios grupos coexisten hasta capacidad_camping.
        select_for_update() evita race conditions. [OWASP 2.1, 2.11]
        """
        personas_ocupadas = Reservacion.objects.select_for_update().filter(
            parque=parque,
            tipo_visita=TipoVisita.CAMPING,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,
            fecha_termino__gt=fecha_inicio
        ).aggregate(total=Sum('numero_personas'))['total'] or 0

        disponible = parque.capacidad_camping - personas_ocupadas
        if numero_personas > disponible:
            raise ValueError(
                f"Sin disponibilidad en camping. "
                f"Lugares disponibles: {disponible}, solicitados: {numero_personas}."
            )

    @classmethod
    def crear_reservacion(cls, cliente, parque, fecha_inicio, fecha_termino,
                          numero_personas, tipo_visita, cabana=None):
        """
        CU-03 — Punto de entrada único para crear reservaciones.
        Para CABANA: cabana debe ser una instancia de Cabana del parque correcto.
        Para CAMPING: cabana debe ser None.
        transaction.atomic() garantiza consistencia ante concurrencia. [OWASP 2.1, 2.11]
        """
        if tipo_visita == TipoVisita.CABANA and cabana is None:
            raise ValueError("Debes seleccionar una cabaña para este tipo de reservación.")
        if tipo_visita == TipoVisita.CAMPING and cabana is not None:
            raise ValueError("Las reservaciones de camping no requieren cabaña.")
        if cabana and cabana.parque_id != parque.id:
            raise ValueError("La cabaña seleccionada no pertenece al parque indicado.")

        with transaction.atomic():
            cls.verificar_periodo_festival(fecha_inicio, fecha_termino)
            cls.verificar_no_martes(fecha_inicio, fecha_termino)

            if tipo_visita == TipoVisita.CABANA:
                cls.verificar_disponibilidad_cabana(
                    cabana, fecha_inicio, fecha_termino, numero_personas
                )
            else:
                cls.verificar_disponibilidad_camping(
                    parque, fecha_inicio, fecha_termino, numero_personas
                )

            return Reservacion.objects.create(
                cliente=cliente,
                parque=parque,
                cabana=cabana,
                fecha_inicio=fecha_inicio,
                fecha_termino=fecha_termino,
                numero_personas=numero_personas,
                tipo_visita=tipo_visita
            )
