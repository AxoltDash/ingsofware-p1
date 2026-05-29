import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404, redirect, render

from reservaciones.services import ServicioCorreo
from .decorators import requiere_admin
from .forms import LoginForm, RecuperacionForm, RegistroClienteForm, RestablecerForm
from .models import Administrador, Cliente, PasswordResetToken, Usuario

logger = logging.getLogger('cepuac')
logger_admin = logging.getLogger('cepuac.admin')


def registro(request):
    """CU-01: registro de nuevo cliente."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            logger.info(f"Nuevo cliente registrado id={user.id}")
            return redirect('home')
    else:
        form = RegistroClienteForm()

    return render(request, 'usuarios/registro.html', {'form': form})


def iniciar_sesion(request):
    """CU-08: login con email y contraseña."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            request.session.cycle_key()  # [OWASP 2.4] previene session fixation
            return redirect('home')
    else:
        form = LoginForm(request)

    return render(request, 'usuarios/login.html', {'form': form})


def cerrar_sesion(request):
    """RF-01.3: logout que invalida completamente la sesión."""
    request.session.flush()  # [OWASP 2.4] destruye la sesión entera
    logout(request)
    return redirect('login')


def solicitar_recuperacion(request):
    """RF-01.6: solicitud de recuperación de contraseña por correo."""
    if request.method == 'POST':
        form = RecuperacionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            usuario = Cliente.objects.filter(email=email).first()
            if usuario:
                token_obj = PasswordResetToken.crear_para(usuario)
                ServicioCorreo.enviar_recuperacion(usuario, token_obj.token)
                logger.info(f"Recuperación solicitada usuario_id={usuario.id}")
            # [OWASP 2.3] misma respuesta aunque el correo no exista
            return render(request, 'usuarios/recuperar.html', {'form': form, 'enviado': True})
    else:
        form = RecuperacionForm()

    return render(request, 'usuarios/recuperar.html', {'form': form, 'enviado': False})


def restablecer_contrasenia(request, token):
    """RF-01.6: restablecimiento de contraseña usando el token del correo."""
    token_obj = get_object_or_404(PasswordResetToken, token=token)

    if not token_obj.es_valido():
        return render(request, 'usuarios/restablecer.html', {'expirado': True})

    if request.method == 'POST':
        form = RestablecerForm(token_obj.usuario, request.POST)
        if form.is_valid():
            form.save()
            token_obj.usado = True
            token_obj.save()
            logger.info(f"Contraseña restablecida usuario_id={token_obj.usuario_id}")
            return redirect('login')
    else:
        form = RestablecerForm(token_obj.usuario)

    return render(request, 'usuarios/restablecer.html', {'form': form, 'expirado': False})


# ── Panel de administrador — usuarios ─────────────────────────────────────────

@requiere_admin
def admin_usuarios(request):
    """HU-22: lista de clientes y administradores del sistema."""
    clientes = Cliente.objects.all().order_by('-is_active', 'email')
    admins = Administrador.objects.all().order_by('-is_active', 'email')
    return render(request, 'usuarios/admin_usuarios.html', {
        'clientes': clientes,
        'admins': admins,
    })


@requiere_admin
def desactivar_usuario(request, usuario_id):
    """HU-23: soft delete de usuario. No puede desactivarse a sí mismo. [OWASP 2.5, 2.7]"""
    if request.method != 'POST':
        return redirect('admin_usuarios')
    if usuario_id == request.user.id:
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
        return redirect('admin_usuarios')
    usuario = get_object_or_404(Usuario, id=usuario_id)
    usuario.is_active = False
    usuario.save(update_fields=['is_active'])
    logger_admin.warning(f"Usuario desactivado id={usuario_id} admin_id={request.user.id}")
    messages.success(request, f'Usuario {usuario.email} desactivado.')
    return redirect('admin_usuarios')
