import logging

from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.decorators import requiere_admin
from .forms import CabanaForm, CapacidadCampingForm, ParqueForm
from .models import Cabana, Parque

logger = logging.getLogger('cepuac.admin')


def api_marcadores(request):
    """RF-02: coordenadas de parques activos para el mapa interactivo."""
    parques = Parque.objects.filter(activo=True).values(
        'id', 'nombre', 'latitud', 'longitud', 'direccion'
    )
    return JsonResponse(list(parques), safe=False)


# ── Gestión de parques ────────────────────────────────────────────────────────

@requiere_admin
def admin_parques(request):
    """HU-12: lista completa de parques con acciones de gestión."""
    parques = Parque.objects.all().order_by('-activo', 'nombre')
    return render(request, 'parques/admin_parques.html', {'parques': parques})


@requiere_admin
def crear_parque(request):
    """HU-13: alta de nuevo parque. [OWASP 2.7]"""
    form = ParqueForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        parque = form.save()
        logger.info(f"Parque creado id={parque.id} admin_id={request.user.id}")
        messages.success(request, f'Parque "{parque.nombre}" creado correctamente.')
        return redirect('admin_parques')
    return render(request, 'parques/form_parque.html', {
        'form': form,
        'titulo': 'Nuevo parque',
    })


@requiere_admin
def editar_parque(request, parque_id):
    """HU-14: editar datos de un parque. [OWASP 2.7]"""
    parque = get_object_or_404(Parque, id=parque_id)
    form = ParqueForm(request.POST or None, instance=parque)
    if request.method == 'POST' and form.is_valid():
        form.save()
        logger.info(f"Parque editado id={parque.id} admin_id={request.user.id}")
        messages.success(request, f'Parque "{parque.nombre}" actualizado.')
        return redirect('admin_parques')
    return render(request, 'parques/form_parque.html', {
        'form': form,
        'titulo': f'Editar: {parque.nombre}',
        'parque': parque,
    })


@requiere_admin
def eliminar_parque(request, parque_id):
    """HU-15: soft delete de parque — conserva historial de reservaciones. [OWASP 2.7]"""
    parque = get_object_or_404(Parque, id=parque_id)
    if request.method == 'POST':
        parque.activo = False
        parque.save(update_fields=['activo'])
        logger.warning(f"Parque desactivado id={parque_id} admin_id={request.user.id}")
        messages.success(request, f'Parque "{parque.nombre}" desactivado.')
    return redirect('admin_parques')


# ── Gestión de cabañas ────────────────────────────────────────────────────────

@requiere_admin
def admin_cabanas(request, parque_id):
    """HU-17: cabañas del parque + formulario de capacidad camping."""
    parque = get_object_or_404(Parque, id=parque_id)
    cabanas = parque.cabanas.order_by('-activo', 'nombre')
    form_capacidad = CapacidadCampingForm(
        initial={'capacidad_camping': parque.capacidad_camping}
    )
    return render(request, 'parques/admin_cabanas.html', {
        'parque': parque,
        'cabanas': cabanas,
        'form_capacidad': form_capacidad,
    })


@requiere_admin
def crear_cabana(request, parque_id):
    """HU-18: agregar cabaña al parque; actualiza tiene_cabanas si es la primera. [OWASP 2.7]"""
    parque = get_object_or_404(Parque, id=parque_id, activo=True)
    form = CabanaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cabana = form.save(commit=False)
        cabana.parque = parque
        cabana.save()
        if not parque.tiene_cabanas:
            parque.tiene_cabanas = True
            parque.save(update_fields=['tiene_cabanas'])
        logger.info(
            f"Cabaña creada id={cabana.id} parque_id={parque_id} admin_id={request.user.id}"
        )
        messages.success(request, f'Cabaña "{cabana.nombre}" creada correctamente.')
        return redirect('admin_cabanas', parque_id=parque_id)
    return render(request, 'parques/form_cabana.html', {
        'form': form,
        'parque': parque,
        'titulo': 'Nueva cabaña',
    })


@requiere_admin
def editar_cabana(request, cabana_id):
    """HU-19: editar nombre y capacidad de una cabaña. [OWASP 2.7]"""
    cabana = get_object_or_404(Cabana, id=cabana_id)
    form = CabanaForm(request.POST or None, instance=cabana)
    if request.method == 'POST' and form.is_valid():
        form.save()
        logger.info(f"Cabaña editada id={cabana.id} admin_id={request.user.id}")
        messages.success(request, f'Cabaña "{cabana.nombre}" actualizada.')
        return redirect('admin_cabanas', parque_id=cabana.parque_id)
    return render(request, 'parques/form_cabana.html', {
        'form': form,
        'parque': cabana.parque,
        'titulo': f'Editar: {cabana.nombre}',
        'cabana': cabana,
    })


@requiere_admin
def desactivar_cabana(request, cabana_id):
    """HU-20: soft delete de cabaña — bloqueado si hay reservaciones activas. [OWASP 2.5, 2.7]"""
    if request.method != 'POST':
        return redirect('admin_parques')
    cabana = get_object_or_404(Cabana, id=cabana_id)
    from reservaciones.models import EstadoReservacion, Reservacion
    tiene_activas = Reservacion.objects.filter(
        cabana=cabana, estado=EstadoReservacion.ACTIVA
    ).exists()
    if tiene_activas:
        messages.error(
            request,
            f'No se puede desactivar "{cabana.nombre}": tiene reservaciones activas.'
        )
    else:
        cabana.activo = False
        cabana.save(update_fields=['activo'])
        logger.warning(f"Cabaña desactivada id={cabana_id} admin_id={request.user.id}")
        messages.success(request, f'Cabaña "{cabana.nombre}" desactivada.')
    return redirect('admin_cabanas', parque_id=cabana.parque_id)


@requiere_admin
def gestionar_disponibilidad(request, parque_id):
    """CU-07: actualizar capacidad de camping — validada contra ocupación actual. [OWASP 2.1, 2.7]"""
    if request.method != 'POST':
        return redirect('admin_cabanas', parque_id=parque_id)
    parque = get_object_or_404(Parque, id=parque_id)
    form = CapacidadCampingForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Valor inválido para la capacidad de camping.')
        return redirect('admin_cabanas', parque_id=parque_id)

    nueva_capacidad = form.cleaned_data['capacidad_camping']

    from reservaciones.models import EstadoReservacion, Reservacion, TipoVisita
    ocupacion_actual = (
        Reservacion.objects
        .filter(
            parque=parque,
            tipo_visita=TipoVisita.CAMPING,
            estado=EstadoReservacion.ACTIVA,
        )
        .aggregate(total=Sum('numero_personas'))['total'] or 0
    )

    if nueva_capacidad < ocupacion_actual:
        messages.error(
            request,
            f'La nueva capacidad ({nueva_capacidad}) es menor que la ocupación actual '
            f'({ocupacion_actual} personas con reservaciones activas).'
        )
        return redirect('admin_cabanas', parque_id=parque_id)

    parque.capacidad_camping = nueva_capacidad
    parque.save(update_fields=['capacidad_camping'])
    logger.info(
        f"Capacidad camping actualizada parque_id={parque_id} "
        f"nueva={nueva_capacidad} admin_id={request.user.id}"
    )
    messages.success(request, f'Capacidad de camping actualizada a {nueva_capacidad} personas.')
    return redirect('admin_cabanas', parque_id=parque_id)
