from datetime import date, timedelta
from django.core import mail
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from parques.models import Cabana, Parque
from reservaciones.models import EstadoReservacion, Reservacion, TipoVisita
from reservaciones.services import GestorReservaciones
from usuarios.models import Cliente as ClienteModel, PasswordResetToken

# ---------------------------------------------------------------------------
# Fechas de referencia
# Restricciones del sistema que afectan los tests:
#   1.- Solo se puede reservar de junio a agosto.
#   2.- Ningún día del rango puede ser martes.
#
# Calendario junio 2026:
#   Lu Ma Mi Ju Vi
#    1  2  3  4  5  martes = 2, 9, 16, 23, 30
#    8  9 10 11 12
# ---------------------------------------------------------------------------
INICIO_VALIDO     = date(2026, 6, 3)
FIN_VALIDO        = date(2026, 6, 5)
INICIO_CON_MARTES = date(2026, 6, 1)
FIN_CON_MARTES    = date(2026, 6, 3)
MARTES_SOLO       = date(2026, 6, 2)
INICIO_ADYACENTE  = date(2026, 6, 5)
FIN_ADYACENTE     = date(2026, 6, 7)
INICIO_INVALIDO   = date(2026, 5, 3)
FIN_INVALIDO      = date(2026, 5, 5)


# Funciones auxiliares
def crear_parque(capacidad_camping=10, tiene_cabanas=True):
    """Crea un Parque de prueba con valores razonables."""
    return Parque.objects.create(
        nombre='Parque Test',
        direccion='Calle Falsa 123',
        horario='08:00-18:00',
        latitud='19.432608',
        longitud='-99.133209',
        tiene_cabanas=tiene_cabanas,
        capacidad_camping=capacidad_camping,
        activo=True,
    )


def crear_cabana(parque, capacidad=4):
    """Crea una Cabaña activa dentro del parque dado."""
    return Cabana.objects.create(
        parque=parque,
        nombre='Cabaña 1',
        capacidad=capacidad,
        activo=True,
    )


def crear_cliente(email='cliente@test.com', password='123!Pboart'):
    """Crea un Cliente (subclase de Usuario) listo para usar en vistas."""
    return ClienteModel.objects.create_user(email=email, password=password)


# Pruebas del gestor de reservaciones

class GestorReservacionesTests(TestCase):
    """
    Se prueba cada función por separado y luego se hace una prueba 
    de transacción.
    """

    def setUp(self):
        self.parque = crear_parque(capacidad_camping=10)
        self.cabana = crear_cabana(self.parque, capacidad=4)
        self.cliente = crear_cliente()

    def test_periodo_festival_junio_valido(self):
        """Fechas dentro de junio no deben lanzar excepción."""
        GestorReservaciones.verificar_periodo_festival(INICIO_VALIDO, FIN_VALIDO)

    def test_periodo_festival_agosto_valido(self):
        """Todo agosto es válido."""
        GestorReservaciones.verificar_periodo_festival(date(2026, 8, 1), date(2026, 8, 10))

    def test_periodo_festival_mayo_invalido(self):
        """Mayo está fuera del periodo debe lanzar ValueError."""
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_periodo_festival(INICIO_INVALIDO, FIN_INVALIDO)

    def test_periodo_festival_septiembre_invalido(self):
        """Septiembre está fuera del periodo debe lanzar ValueError."""
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_periodo_festival(date(2026, 9, 1), date(2026, 9, 5))

    def test_periodo_festival_inicio_invalido_fin_valido(self):
        """Si solo fecha_inicio está fuera del periodo, igual debe fallar."""
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_periodo_festival(date(2026, 5, 30), date(2026, 6, 5))

    def test_mantenimiento_rango_sin_martes(self):
        """Rango mié-vie: no se incluye ningun martes"""
        GestorReservaciones.verificar_dia_mantenimiento(INICIO_VALIDO, FIN_VALIDO)

    def test_mantenimiento_rango_incluye_martes(self):
        """Rango lun-mié: contiene martes 2 jun debe lanzar ValueError."""
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_dia_mantenimiento(INICIO_CON_MARTES, FIN_CON_MARTES)

    def test_mantenimiento_dia_unico_martes(self):
        """Un solo día que es martes es inválido."""
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_dia_mantenimiento(MARTES_SOLO, MARTES_SOLO)

    def test_mantenimiento_dia_unico_no_martes(self):
        """Un solo día que no es martes (miércoles 3 jun) debe pasar."""
        GestorReservaciones.verificar_dia_mantenimiento(INICIO_VALIDO, INICIO_VALIDO)

    def test_disponibilidad_cabana_libre(self):
        """Una cabaña sin reservar debe estar disponible."""
        GestorReservaciones.verificar_disponibilidad_cabana(
            self.cabana, INICIO_VALIDO, FIN_VALIDO, 2
        )

    def test_disponibilidad_cabana_ocupada_solapada(self):
        """El reservar una cabaña ya apartada es una acción inválida."""
        Reservacion.objects.create(
            cliente=self.cliente,
            parque=self.parque,
            cabana=self.cabana,
            fecha_inicio=INICIO_VALIDO,
            fecha_termino=FIN_VALIDO,
            numero_personas=2,
            tipo_visita=TipoVisita.CABANA,
            estado=EstadoReservacion.ACTIVA,
        )
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_disponibilidad_cabana(
                self.cabana, INICIO_VALIDO, FIN_VALIDO, 2
            )

    def test_disponibilidad_cabana_cancelada_no_bloquea(self):
        """El cancelar una reservación implica que la cabaña este disponible de nuevo"""
        Reservacion.objects.create(
            cliente=self.cliente,
            parque=self.parque,
            cabana=self.cabana,
            fecha_inicio=INICIO_VALIDO,
            fecha_termino=FIN_VALIDO,
            numero_personas=2,
            tipo_visita=TipoVisita.CABANA,
            estado=EstadoReservacion.CANCELADA,
        )
        GestorReservaciones.verificar_disponibilidad_cabana(
            self.cabana, INICIO_VALIDO, FIN_VALIDO, 2
        )

    def test_disponibilidad_cabana_fechas_adyacentes_no_solapan(self):
        """
        Reservación que termina el día que empieza la nueva es una acción válida.
        """
        Reservacion.objects.create(
            cliente=self.cliente,
            parque=self.parque,
            cabana=self.cabana,
            fecha_inicio=INICIO_VALIDO,
            fecha_termino=FIN_VALIDO,
            numero_personas=2,
            tipo_visita=TipoVisita.CABANA,
            estado=EstadoReservacion.ACTIVA,
        )
        GestorReservaciones.verificar_disponibilidad_cabana(
            self.cabana, INICIO_ADYACENTE, FIN_ADYACENTE, 2
        )

    def test_disponibilidad_cabana_excede_capacidad(self):
        """Número de personas mayor que capacidad debe lanzar ValueError."""
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_disponibilidad_cabana(
                self.cabana, INICIO_VALIDO, FIN_VALIDO, 99
            )

    def test_disponibilidad_camping_con_espacio(self):
        """Parque con capacidad suficiente debe aceptar la reservación."""
        GestorReservaciones.verificar_disponibilidad_camping(
            self.parque, INICIO_VALIDO, FIN_VALIDO, 5
        )

    def test_disponibilidad_camping_sin_espacio(self):
        """La capacidad del camping nunca debe ser superada."""
        Reservacion.objects.create(
            cliente=self.cliente,
            parque=self.parque,
            fecha_inicio=INICIO_VALIDO,
            fecha_termino=FIN_VALIDO,
            numero_personas=8,
            tipo_visita=TipoVisita.CAMPING,
            estado=EstadoReservacion.ACTIVA,
        )
        with self.assertRaises(ValueError):
            GestorReservaciones.verificar_disponibilidad_camping(
                self.parque, INICIO_VALIDO, FIN_VALIDO, 5
            )

    def test_disponibilidad_camping_cancelada_no_cuenta(self):
        """Las reservaciones canceladas no se suman a la ocupación."""
        Reservacion.objects.create(
            cliente=self.cliente,
            parque=self.parque,
            fecha_inicio=INICIO_VALIDO,
            fecha_termino=FIN_VALIDO,
            numero_personas=9,
            tipo_visita=TipoVisita.CAMPING,
            estado=EstadoReservacion.CANCELADA,
        )
        GestorReservaciones.verificar_disponibilidad_camping(
            self.parque, INICIO_VALIDO, FIN_VALIDO, 9
        )

    def test_crear_reservacion_cabana_exitosa(self):
        """Flujo de creación de una reservación a una cabaña"""
        reservacion = GestorReservaciones.crear_reservacion(
            cliente=self.cliente,
            parque=self.parque,
            fecha_inicio=INICIO_VALIDO,
            fecha_termino=FIN_VALIDO,
            numero_personas=2,
            tipo_visita=TipoVisita.CABANA,
            cabana=self.cabana,
        )
        self.assertIsNotNone(reservacion.pk)
        self.assertEqual(reservacion.estado, EstadoReservacion.ACTIVA)

    def test_crear_reservacion_camping_exitosa(self):
        """Flujo de creación de una reservación de camping"""
        reservacion = GestorReservaciones.crear_reservacion(
            cliente=self.cliente,
            parque=self.parque,
            fecha_inicio=INICIO_VALIDO,
            fecha_termino=FIN_VALIDO,
            numero_personas=3,
            tipo_visita=TipoVisita.CAMPING,
            cabana=None,
        )
        self.assertIsNone(reservacion.cabana)
        self.assertEqual(reservacion.tipo_visita, TipoVisita.CAMPING)

    def test_crear_reservacion_cabana_sin_especificar_cabana(self):
        """La cabaña a reservar debe exisitr."""
        with self.assertRaises(ValueError):
            GestorReservaciones.crear_reservacion(
                cliente=self.cliente,
                parque=self.parque,
                fecha_inicio=INICIO_VALIDO,
                fecha_termino=FIN_VALIDO,
                numero_personas=2,
                tipo_visita=TipoVisita.CABANA,
                cabana=None,
            )

    def test_crear_reservacion_camping_con_cabana(self):
        """Un camping no debe especificar una cabaña"""
        with self.assertRaises(ValueError):
            GestorReservaciones.crear_reservacion(
                cliente=self.cliente,
                parque=self.parque,
                fecha_inicio=INICIO_VALIDO,
                fecha_termino=FIN_VALIDO,
                numero_personas=2,
                tipo_visita=TipoVisita.CAMPING,
                cabana=self.cabana,
            )

    def test_crear_reservacion_cabana_de_otro_parque(self):
        """Cabaña que no pertenece al parque indicado debe lanzar ValueError."""
        otro_parque = crear_parque()
        cabana_ajena = Cabana.objects.create(
            parque=otro_parque, nombre='Cabaña X', capacidad=4, activo=True
        )
        with self.assertRaises(ValueError):
            GestorReservaciones.crear_reservacion(
                cliente=self.cliente,
                parque=self.parque,     
                fecha_inicio=INICIO_VALIDO,
                fecha_termino=FIN_VALIDO,
                numero_personas=2,
                tipo_visita=TipoVisita.CABANA,
                cabana=cabana_ajena,  
            )

    def test_crear_reservacion_rechaza_mes_invalido(self):
        """crear_reservacion debe propagar el ValueError de verificar_periodo_festival."""
        with self.assertRaises(ValueError):
            GestorReservaciones.crear_reservacion(
                cliente=self.cliente,
                parque=self.parque,
                fecha_inicio=INICIO_INVALIDO,
                fecha_termino=FIN_INVALIDO,
                numero_personas=2,
                tipo_visita=TipoVisita.CAMPING,
            )

    def test_crear_reservacion_rechaza_martes(self):
        """crear_reservacion debe propagar el ValueError de verificar_dia_mantenimiento."""
        with self.assertRaises(ValueError):
            GestorReservaciones.crear_reservacion(
                cliente=self.cliente,
                parque=self.parque,
                fecha_inicio=INICIO_CON_MARTES,
                fecha_termino=FIN_CON_MARTES,
                numero_personas=2,
                tipo_visita=TipoVisita.CAMPING,
            )

# Pruebas del modulo para resetear la contraseña

class PasswordResetTokenTests(TestCase):
    """
    Cubre la creación del token, su validez y la invalidación de tokens
    anteriores al crear uno nuevo.
    """

    def setUp(self):
        self.usuario = crear_cliente()

    def test_crear_para_genera_token_unico(self):
        """El token generado no debe ser vacío."""
        token_obj = PasswordResetToken.crear_para(self.usuario)
        self.assertTrue(len(token_obj.token) > 0)

    def test_crear_para_expira_en_30_minutos(self):
        """El token debe expirar aproximadamente 30 minutos después de ahora."""
        token_obj = PasswordResetToken.crear_para(self.usuario)
        delta = token_obj.expira - timezone.now()
        self.assertAlmostEqual(delta.total_seconds(), 1800, delta=5)

    def test_crear_para_invalida_tokens_anteriores(self):
        """
        Al crear un nuevo token, los anteriores no usados deben marcarse como
        usados para impedir que un enlace viejo siga funcionando.
        """
        token_viejo = PasswordResetToken.crear_para(self.usuario)
        PasswordResetToken.crear_para(self.usuario) 
        token_viejo.refresh_from_db()
        self.assertTrue(token_viejo.usado)

    def test_es_valido_token_fresco(self):
        """Un token recién creado debe ser válido."""
        token_obj = PasswordResetToken.crear_para(self.usuario)
        self.assertTrue(token_obj.es_valido())

    def test_es_valido_token_usado(self):
        """Un token marcado como usado no debe ser válido."""
        token_obj = PasswordResetToken.crear_para(self.usuario)
        token_obj.usado = True
        token_obj.save()
        self.assertFalse(token_obj.es_valido())

    def test_es_valido_token_vencido(self):
        """Un token con fecha de expiración en el pasado no debe ser válido."""
        token_obj = PasswordResetToken.crear_para(self.usuario)
        token_obj.expira = timezone.now() - timedelta(minutes=1)
        token_obj.save()
        self.assertFalse(token_obj.es_valido())

# Pruebas para la verificación de disponibilidad de cabañas.

class CabanaDisponibilidadTests(TestCase):
    """
    Este método es la primera línea de verificación de disponibilidad;
    GestorReservaciones lo complementa con select_for_update().
    """

    def setUp(self):
        self.parque  = crear_parque()
        self.cabana  = crear_cabana(self.parque)
        self.cliente = crear_cliente()

    def _reservar(self, inicio, fin, estado=EstadoReservacion.ACTIVA):
        """Crea una reservación de cabaña directamente en la base de datos."""
        return Reservacion.objects.create(
            cliente=self.cliente,
            parque=self.parque,
            cabana=self.cabana,
            fecha_inicio=inicio,
            fecha_termino=fin,
            numero_personas=2,
            tipo_visita=TipoVisita.CABANA,
            estado=estado,
        )

    def test_cabana_disponible_sin_reservaciones(self):
        self.assertTrue(self.cabana.esta_disponible(INICIO_VALIDO, FIN_VALIDO))

    def test_cabana_no_disponible_con_reservacion_solapada(self):
        self._reservar(INICIO_VALIDO, FIN_VALIDO)
        self.assertFalse(self.cabana.esta_disponible(INICIO_VALIDO, FIN_VALIDO))

    def test_cabana_disponible_reservacion_cancelada(self):
        """Una reservación cancelada no debe bloquear la cabaña."""
        self._reservar(INICIO_VALIDO, FIN_VALIDO, estado=EstadoReservacion.CANCELADA)
        self.assertTrue(self.cabana.esta_disponible(INICIO_VALIDO, FIN_VALIDO))

    def test_cabana_disponible_fechas_adyacentes(self):
        """Inicio de nueva reservación igual al fin de la existente no es solape."""
        self._reservar(INICIO_VALIDO, FIN_VALIDO)
        self.assertTrue(self.cabana.esta_disponible(FIN_VALIDO, FIN_ADYACENTE))


# Pruebas de vistas de autenticación.

class VistasRegistroTests(TestCase):
    """Pruebas para la vista registro."""

    def test_get_devuelve_200(self):
        response = self.client.get(reverse('registro'))
        self.assertEqual(response.status_code, 200)

    def test_get_usa_plantilla_registro(self):
        response = self.client.get(reverse('registro'))
        self.assertTemplateUsed(response, 'usuarios/registro.html')

    def test_post_valido_crea_cliente_y_redirige(self):
        """Registro exitoso debe crear el Cliente en BD e iniciar sesión."""
        datos = {
            'email':      'nuevo@test.com',
            'first_name': 'Ana',
            'last_name':  'García',
            'password1':  'TestPass123!',
            'password2':  'TestPass123!',
        }
        response = self.client.post(reverse('registro'), datos)
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(ClienteModel.objects.filter(email='nuevo@test.com').exists())

    def test_post_email_duplicado_muestra_error(self):
        """No se puede registrar el mismo email dos veces."""
        crear_cliente('duplicado@test.com')
        datos = {
            'email':      'duplicado@test.com',
            'first_name': 'Luis',
            'last_name':  'Pérez',
            'password1':  'TestPass123!',
            'password2':  'TestPass123!',
        }
        response = self.client.post(reverse('registro'), datos)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_usuario_autenticado_redirige_sin_mostrar_formulario(self):
        """Un usuario ya logueado que visita /registro/ debe ir a home."""
        user = crear_cliente('ya@login.com')
        self.client.force_login(user)
        response = self.client.get(reverse('registro'))
        self.assertRedirects(response, reverse('home'))


class VistasSessionTests(TestCase):
    """Pruebas para login, logout y protección de sesión."""

    def setUp(self):
        self.cliente = crear_cliente()

    @override_settings(AXES_FAILURE_LIMIT=100)
    def test_login_post_valido_redirige(self):
        """Credenciales correctas deben autenticar y redirigir a home."""
        response = self.client.post(reverse('login'), {
            'username': 'cliente@test.com',
            'password': '123!Pboart',
        })
        self.assertRedirects(response, reverse('home'))

    @override_settings(AXES_FAILURE_LIMIT=100)
    def test_login_post_valido_inicia_sesion(self):
        """Después del login, el usuario debe estar autenticado."""
        self.client.post(reverse('login'), {
            'username': 'cliente@test.com',
            'password': '123!Pboart',
        })
        self.assertTrue(self.client.session.get('_auth_user_id'))

    @override_settings(AXES_FAILURE_LIMIT=100)
    def test_login_contrasenia_incorrecta_devuelve_200(self):
        """Credenciales incorrectas no deben redirigir ni autenticar."""
        response = self.client.post(reverse('login'), {
            'username': 'cliente@test.com',
            'password': 'Incorrecta999!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get('_auth_user_id'))

    @override_settings(AXES_FAILURE_LIMIT=100)
    def test_login_rota_session_key(self):
        """
        Tras el login debe generarse un nuevo ID de sesión. 
        session.cycle_key() en la vista lo garantiza.
        """
        self.client.get(reverse('login'))
        session_key_antes = self.client.session.session_key

        self.client.post(reverse('login'), {
            'username': 'cliente@test.com',
            'password': '123!Pboart',
        })
        session_key_despues = self.client.session.session_key

        self.assertNotEqual(session_key_antes, session_key_despues)

    def test_logout_cierra_sesion(self):
        """Después del logout el usuario no debe estar autenticado."""
        self.client.force_login(self.cliente)
        self.client.get(reverse('logout'))
        response = self.client.get(reverse('home'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_redirige_a_login(self):
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_usuario_autenticado_no_ve_login(self):
        """Un usuario ya logueado que visita /login/ debe ir a home."""
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('home'))


class VistasRecuperacionTests(TestCase):
    """
    Pruebas para el flujo de recuperación de contraseña.
    """

    def setUp(self):
        self.cliente = crear_cliente()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacion_email_existente_envia_correo(self):
        """Con un email registrado debe enviarse exactamente un correo."""
        self.client.post(reverse('recuperar_contrasenia'), {'email': 'cliente@test.com'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('cliente@test.com', mail.outbox[0].to)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacion_email_inexistente_no_envia_correo(self):
        """
        Con un email no registrado NO debe enviarse correo, pero la respuesta
        debe ser idéntica (200 con enviado=True) para evitar enumeración de
        usuarios (OWASP 2.3).
        """
        response = self.client.post(
            reverse('recuperar_contrasenia'), {'email': 'noexiste@test.com'}
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['enviado'])

    def test_restablecer_token_valido_devuelve_200(self):
        """Un token fresco debe mostrar el formulario de nueva contraseña."""
        token_obj = PasswordResetToken.crear_para(self.cliente)
        url = reverse('restablecer_contrasenia', args=[token_obj.token])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['expirado'])

    def test_restablecer_token_vencido_muestra_expirado(self):
        """Token con fecha de expiración pasada debe marcar expirado=True."""
        token_obj = PasswordResetToken.crear_para(self.cliente)
        token_obj.expira = timezone.now() - timedelta(minutes=1)
        token_obj.save()
        url = reverse('restablecer_contrasenia', args=[token_obj.token])
        response = self.client.get(url)
        self.assertTrue(response.context['expirado'])

    def test_restablecer_post_valido_cambia_contrasenia(self):
        """POST con contraseñas válidas debe cambiar la contraseña y marcar el token como usado."""
        token_obj = PasswordResetToken.crear_para(self.cliente)
        url = reverse('restablecer_contrasenia', args=[token_obj.token])
        response = self.client.post(url, {
            'new_password1': 'NuevaPass456!',
            'new_password2': 'NuevaPass456!',
        })
        self.assertRedirects(response, reverse('login'))
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.usado)

    def test_restablecer_token_ya_usado_muestra_expirado(self):
        """Reutilizar un token ya consumido debe mostrar expirado=True."""
        token_obj = PasswordResetToken.crear_para(self.cliente)
        token_obj.usado = True
        token_obj.save()
        url = reverse('restablecer_contrasenia', args=[token_obj.token])
        response = self.client.get(url)
        self.assertTrue(response.context['expirado'])


# Pruebas vistas públicas.

class VistasPublicasTests(TestCase):
    """
    Pruebas de integración para las vistas públicas:
    home y bosques.
    """

    def setUp(self):
        self.parque_activo   = crear_parque()
        self.parque_inactivo = Parque.objects.create(
            nombre='Parque Cerrado',
            direccion='Calle X',
            horario='08:00-18:00',
            latitud='19.0',
            longitud='-99.0',
            activo=False,
        )
        self.cliente = crear_cliente()

    def test_home_devuelve_200(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_usa_plantilla_correcta(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'elProyecto/home.html')

    def test_bosques_devuelve_200(self):
        response = self.client.get(reverse('bosques'))
        self.assertEqual(response.status_code, 200)

    def test_bosques_solo_muestra_parques_activos(self):
        """El contexto 'parques' no debe incluir parques con activo=False."""
        response = self.client.get(reverse('bosques'))
        parques_en_contexto = list(response.context['parques'])
        self.assertIn(self.parque_activo,   parques_en_contexto)
        self.assertNotIn(self.parque_inactivo, parques_en_contexto)

    def test_url_inexistente_devuelve_404(self):
        response = self.client.get('/esta/ruta/no/existe/')
        self.assertEqual(response.status_code, 404)