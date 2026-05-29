import logging

from django.shortcuts import get_object_or_404, redirect, render

from usuarios.decorators import requiere_admin, requiere_cliente
from .models import EstadoReservacion, Reservacion

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
