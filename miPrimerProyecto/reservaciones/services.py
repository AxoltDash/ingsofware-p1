import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Sum

from .models import Reservacion, TipoVisita, EstadoReservacion

logger = logging.getLogger('cepuac')


class GestorReservaciones:

    @staticmethod
    def verificar_periodo_festival(fecha_inicio, fecha_termino):
        """RN-01: solo junio-agosto """
        meses_validos = {6, 7, 8}  # set para búsqueda O(1)
        if fecha_inicio.month not in meses_validos or fecha_termino.month not in meses_validos:
            raise ValueError("Las reservaciones solo son válidas de junio a agosto.")

    @staticmethod
    def verificar_dia_mantenimiento(fecha_inicio, fecha_termino):
        """RN-02: ningún día del rango puede ser martes """
        fecha = fecha_inicio
        while fecha <= fecha_termino:
            if fecha.weekday() == 1:  # weekday(): el parametro se mueve como 0=lunes, 1=martes, ..., 6=domingo
                raise ValueError("Las reservaciones no pueden incluir días martes.")
            fecha += timedelta(days=1)

    @staticmethod
    def cabanas_disponibles(parque, fecha_inicio, fecha_termino, numero_personas):
        """
        Devuelve cabañas del parque que cumplen ambas condiciones:
          1. Capacidad individual >= numero_personas
          2. Sin reservación ACTIVA solapada en el rango de fechas
        Usado para mostrar opciones al cliente antes de reservar. 
        """
        from parques.models import Cabana  # importación local para romper el circular import: reservaciones ↔ parques

        # obtener solo los IDs de cabañas ya ocupadas en ese rango
        cabanas_ocupadas_ids = Reservacion.objects.filter(
            parque=parque,
            tipo_visita=TipoVisita.CABANA,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,  # condición de solapamiento: empieza antes de que termine la solicitada
            fecha_termino__gt=fecha_inicio   # y termina después de que empiece la solicitada
        ).values_list('cabana_id', flat=True)  # flat=True devuelve una lista plana de IDs, no tuplas (id,)

        return Cabana.objects.filter(
            parque=parque,
            activo=True,
            capacidad__gte=numero_personas       # gte = "greater than or equal": solo cabañas donde cabe el grupo
        ).exclude(id__in=cabanas_ocupadas_ids)   # excluye las ocupadas en esas fechas

    @staticmethod
    def verificar_disponibilidad_cabana(cabana, fecha_inicio, fecha_termino, numero_personas):
        """
        Verifica que una cabaña específica esté libre y tenga capacidad suficiente.
        select_for_update() evita race conditions.
        """
        if numero_personas > cabana.capacidad:
            raise ValueError(
                f"El grupo ({numero_personas} personas) excede la capacidad "
                f"de {cabana.nombre} ({cabana.capacidad} personas máx)."
            )
        solapada = Reservacion.objects.select_for_update().filter(  # select_for_update bloquea las filas hasta que termine el atomic(), impide que dos peticiones simultáneas lean el mismo "libre"
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
        personas_ocupadas = Reservacion.objects.select_for_update().filter(  # lock para evitar sobre-reservaciones por concurrencia
            parque=parque,
            tipo_visita=TipoVisita.CAMPING,
            estado=EstadoReservacion.ACTIVA,
            fecha_inicio__lt=fecha_termino,
            fecha_termino__gt=fecha_inicio
        ).aggregate(total=Sum('numero_personas'))['total'] or 0  # or 0 porque aggregate devuelve None si no hay filas que sumen

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
        transaction.atomic() garantiza consistencia ante concurrencia.
        """
        # validaciones previas al lock: no necesitan transacción porque solo leen parámetros de entrada
        if tipo_visita == TipoVisita.CABANA and cabana is None:
            raise ValueError("Debes seleccionar una cabaña para este tipo de reservación.")
        if tipo_visita == TipoVisita.CAMPING and cabana is not None:
            raise ValueError("Las reservaciones de camping no requieren cabaña.")
        if cabana and cabana.parque_id != parque.id:  # _id evita cargar el objeto parque completo solo para comparar
            raise ValueError("La cabaña seleccionada no pertenece al parque indicado.")

        with transaction.atomic():  # todo lo que sigue se ejecuta como una sola operación atómica; si algo falla, se revierte todo
            cls.verificar_periodo_festival(fecha_inicio, fecha_termino)
            cls.verificar_dia_mantenimiento(fecha_inicio, fecha_termino)

            if tipo_visita == TipoVisita.CABANA:
                cls.verificar_disponibilidad_cabana(  # valida capacidad y solapamiento con lock
                    cabana, fecha_inicio, fecha_termino, numero_personas
                )
            else:
                cls.verificar_disponibilidad_camping(  # suma personas acumuladas y verifica contra capacidad_camping con lock
                    parque, fecha_inicio, fecha_termino, numero_personas
                )

            return Reservacion.objects.create(
                cliente=cliente,
                parque=parque,
                cabana=cabana,              # None para camping; Reservacion.cabana tiene null=True
                fecha_inicio=fecha_inicio,
                fecha_termino=fecha_termino,
                numero_personas=numero_personas,
                tipo_visita=tipo_visita
            )


class ServicioCorreo:
    """
    Singleton — agrupa todos los envíos de correo del sistema.
    En dev (DEBUG=True) el backend es console: los correos se imprimen en terminal, no se envían.
    En prod el backend es SMTP con TLS [OWASP 2.9].
    [OWASP 2.7] Los métodos loggean solo IDs, nunca contenido personal ni contraseñas.
    """
    _instance = None

    def __new__(cls):
        # garantiza una sola instancia durante todo el ciclo de vida del proceso
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def enviar_confirmacion(reservacion):
        """RF-03.2: notifica al cliente cuando su reservación es creada exitosamente."""
        cabana_info = f" — {reservacion.cabana.nombre}" if reservacion.cabana else ""
        tipo_display = reservacion.get_tipo_visita_display()

        mensaje = (
            f"Hola {reservacion.cliente.first_name},\n\n"
            f"Tu reservación ha sido confirmada:\n\n"
            f"  Parque:   {reservacion.parque.nombre}\n"
            f"  Tipo:     {tipo_display}{cabana_info}\n"
            f"  Personas: {reservacion.numero_personas}\n"
            f"  Desde:    {reservacion.fecha_inicio}\n"
            f"  Hasta:    {reservacion.fecha_termino}\n\n"
            f"Gracias por participar en el Festival Internacional de las Luciérnagas 2026.\n\n"
            f"CEPUAC — Sistema de Reservaciones\n"
        )
        try:
            send_mail(
                subject='Confirmación de reservación — CEPUAC',
                message=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reservacion.cliente.email],
                fail_silently=False,
            )
        except Exception:
            # [OWASP 2.7] loggear solo el ID, nunca el contenido del correo ni datos del cliente
            logger.error(f"Error al enviar confirmación reservacion_id={reservacion.id}")

    @staticmethod
    def enviar_recuperacion(usuario, token):
        """RF-01.6: envía enlace de recuperación de contraseña.
        [OWASP 2.3] El correo contiene solo el enlace, nunca la contraseña actual ni la nueva.
        """
        # construye el enlace absoluto usando BASE_URL del .env
        link = f"{settings.BASE_URL}/auth/restablecer/{token}/"

        mensaje = (
            f"Hola {usuario.first_name},\n\n"
            f"Recibimos una solicitud para restablecer la contraseña de tu cuenta.\n\n"
            f"Usa el siguiente enlace para crear una nueva contraseña (válido 30 minutos):\n"
            f"{link}\n\n"
            f"Si no solicitaste este cambio, ignora este correo — tu contraseña no cambiará.\n\n"
            f"CEPUAC — Sistema de Reservaciones\n"
        )
        try:
            send_mail(
                subject='Recuperación de contraseña — CEPUAC',
                message=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False,
            )
        except Exception:
            # [OWASP 2.7] loggear solo el ID, nunca el token ni el correo del usuario
            logger.error(f"Error al enviar recuperación usuario_id={usuario.id}")
