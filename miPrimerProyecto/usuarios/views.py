import logging

from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404, redirect, render

from reservaciones.services import ServicioCorreo
from .forms import LoginForm, RecuperacionForm, RegistroClienteForm, RestablecerForm
from .models import Cliente, PasswordResetToken

logger = logging.getLogger('cepuac')


def registro(request):
    """CU-01: registro de nuevo cliente."""
    if request.user.is_authenticated:
        return redirect('home')  # no mostrar registro a usuarios ya autenticados

    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            # [OWASP 2.3] create_user() aplica el hasher configurado (Argon2) automáticamente
            user = form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'  # requerido cuando hay múltiples backends
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
        # LoginForm extiende AuthenticationForm; internamente llama a authenticate(request, ...)
        # django-axes intercepta esa llamada y bloquea si superó AXES_FAILURE_LIMIT [OWASP 2.3]
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            request.session.cycle_key()  # [OWASP 2.4] nuevo ID de sesión tras login exitoso, previene session fixation
            return redirect('home')
        # [OWASP 2.3] AuthenticationForm muestra mensaje genérico sin indicar qué campo falló
    else:
        form = LoginForm(request)

    return render(request, 'usuarios/login.html', {'form': form})


def cerrar_sesion(request):
    """RF-01.3: logout que invalida completamente la sesión."""
    request.session.flush()  # [OWASP 2.4] destruye la sesión entera (no solo desvincula al usuario)
    logout(request)          # invalida el token de autenticación de Django
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
                ServicioCorreo.enviar_recuperacion(usuario, token_obj.token)  # en dev imprime en terminal; en prod envía por SMTP
                logger.info(f"Recuperación solicitada usuario_id={usuario.id}")

            # [OWASP 2.3] misma respuesta aunque el correo no exista — evita enumeración de usuarios
            return render(request, 'usuarios/recuperar.html', {'form': form, 'enviado': True})
    else:
        form = RecuperacionForm()

    return render(request, 'usuarios/recuperar.html', {'form': form, 'enviado': False})


def restablecer_contrasenia(request, token):
    """RF-01.6: restablecimiento de contraseña usando el token del correo."""
    token_obj = get_object_or_404(PasswordResetToken, token=token)

    if not token_obj.es_valido():
        # token vencido o ya usado — mostrar mensaje sin revelar cuál fue el problema exacto
        return render(request, 'usuarios/restablecer.html', {'expirado': True})

    if request.method == 'POST':
        form = RestablecerForm(token_obj.usuario, request.POST)
        if form.is_valid():
            form.save()               # guarda nueva contraseña con hash Argon2 [OWASP 2.3]
            token_obj.usado = True    # invalida el token para que no pueda reutilizarse [OWASP 2.6]
            token_obj.save()
            logger.info(f"Contraseña restablecida usuario_id={token_obj.usuario_id}")
            return redirect('login')
    else:
        form = RestablecerForm(token_obj.usuario)

    return render(request, 'usuarios/restablecer.html', {'form': form, 'expirado': False})
