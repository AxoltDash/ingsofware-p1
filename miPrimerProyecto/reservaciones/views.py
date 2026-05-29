import logging
from datetime import date

from django.shortcuts import get_object_or_404, redirect, render

from parques.models import Parque
from usuarios.decorators import requiere_admin, requiere_cliente
from .forms import ReservacionCabanaForm, ReservacionPaso1Form
from .models import EstadoReservacion, Reservacion, TipoVisita
from .services import GestorReservaciones, ServicioCorreo

logger = logging.getLogger('cepuac')


@requiere_cliente
def mis_reservaciones(request):
    """CU-09: el cliente consulta solo SUS reservaciones. [OWASP 2.5]"""
    # filtrar siempre por el usuario autenticado — nunca exponer todas las reservaciones
    reservaciones = (
        Reservacion.objects
        .filter(cliente=request.user.cliente)
        .select_related('parque', 'cabana')  # evita N+1 queries al acceder a parque y cabana
        .order_by('-fecha_creacion')
    )
    return render(request, 'reservaciones/mis_reservaciones.html', {
        'reservaciones': reservaciones,
    })


@requiere_cliente
def cancelar_reservacion(request, reservacion_id):
    """CU-05: el cliente cancela UNA DE SUS reservaciones. [OWASP 2.5 — protección IDOR]"""
    # filtrar por cliente=request.user.cliente evita que un cliente cancele reservaciones ajenas
    # cambiando el ID en la URL (IDOR); si el ID no le pertenece, devuelve 404
    reservacion = get_object_or_404(
        Reservacion,
        id=reservacion_id,
        cliente=request.user.cliente,          # barrera IDOR: solo las propias
        estado=EstadoReservacion.ACTIVA,       # solo se pueden cancelar reservaciones activas
    )

    if request.method == 'POST':
        reservacion.estado = EstadoReservacion.CANCELADA
        reservacion.save()
        ServicioCorreo().enviar_cancelacion(reservacion)
        logger.info(
            f"Reservación cancelada id={reservacion.id} "
            f"cliente_id={request.user.id}"
        )
        return redirect('mis_reservaciones')

    return render(request, 'reservaciones/cancelar_reservacion.html', {
        'reservacion': reservacion,
    })


@requiere_admin
def todas_reservaciones(request):
    """CU-09 Admin: el administrador ve TODAS las reservaciones. [OWASP 2.5]"""
    reservaciones = (
        Reservacion.objects
        .all()
        .select_related('cliente', 'parque', 'cabana')
        .order_by('-fecha_creacion')
    )
    return render(request, 'reservaciones/todas_reservaciones.html', {
        'reservaciones': reservaciones,
    })


@requiere_cliente
def reservar_paso1(request, parque_id):
    """CU-03 paso 1: el cliente elige fechas, personas y tipo de visita."""
    parque = get_object_or_404(Parque, id=parque_id, activo=True)
    form = ReservacionPaso1Form(parque, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        fecha_inicio    = cd['fecha_inicio']
        fecha_termino   = cd['fecha_termino']
        tipo_visita     = cd['tipo_visita']

        try:
            if tipo_visita == TipoVisita.CAMPING:
                reservacion = GestorReservaciones.crear_reservacion(
                    cliente=request.user.cliente,
                    parque=parque,
                    fecha_inicio=fecha_inicio,
                    fecha_termino=fecha_termino,
                    numero_personas=cd['numero_personas'],
                    tipo_visita=TipoVisita.CAMPING,
                )
                ServicioCorreo().enviar_confirmacion(reservacion)
                logger.info(
                    f"Reservación camping creada id={reservacion.id} "
                    f"cliente_id={request.user.id}"
                )
                return redirect('mis_reservaciones')

            # CABANA: guardar fechas en sesión y pasar al paso 2
            request.session['reserva_pendiente'] = {
                'parque_id': parque.id,
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_termino': fecha_termino.isoformat(),
            }
            return redirect('seleccionar_cabana', parque_id=parque.id)

        except ValueError as e:
            form.add_error(None, str(e))

    return render(request, 'reservaciones/reservar_paso1.html', {
        'parque': parque,
        'form': form,
    })


@requiere_cliente
def seleccionar_cabana(request, parque_id):
    """CU-03 paso 2 (cabaña): muestra cabañas disponibles y confirma la reservación."""
    parque = get_object_or_404(Parque, id=parque_id, activo=True)
    pendiente = request.session.get('reserva_pendiente')

    # si no hay datos de sesión o son de otro parque, reiniciar el flujo
    if not pendiente or pendiente.get('parque_id') != parque.id:
        return redirect('reservar_paso1', parque_id=parque.id)

    fecha_inicio  = date.fromisoformat(pendiente['fecha_inicio'])
    fecha_termino = date.fromisoformat(pendiente['fecha_termino'])

    cabanas_qs = GestorReservaciones.cabanas_disponibles(parque, fecha_inicio, fecha_termino)
    form = ReservacionCabanaForm(cabanas_qs, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cabana          = form.cleaned_data['cabana']
        numero_personas = form.cleaned_data['numero_personas']
        try:
            reservacion = GestorReservaciones.crear_reservacion(
                cliente=request.user.cliente,
                parque=parque,
                fecha_inicio=fecha_inicio,
                fecha_termino=fecha_termino,
                numero_personas=numero_personas,
                tipo_visita=TipoVisita.CABANA,
                cabana=cabana,
            )
            ServicioCorreo().enviar_confirmacion(reservacion)
            del request.session['reserva_pendiente']
            logger.info(
                f"Reservación cabaña creada id={reservacion.id} "
                f"cliente_id={request.user.id}"
            )
            return redirect('mis_reservaciones')

        except ValueError as e:
            form.add_error(None, str(e))

    return render(request, 'reservaciones/seleccionar_cabana.html', {
        'parque': parque,
        'form': form,
        'fecha_inicio': fecha_inicio,
        'fecha_termino': fecha_termino,
    })
