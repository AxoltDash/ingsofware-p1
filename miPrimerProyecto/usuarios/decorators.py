from functools import wraps

from django.shortcuts import redirect


def requiere_cliente(view_func):
    """
    Permite el acceso solo a usuarios autenticados con rol Cliente.
    @login_required no es suficiente: un Administrador también está autenticado
    pero no debe acceder a vistas de cliente. [OWASP 2.5]
    """
    @wraps(view_func)  # preserva nombre y docstring de la vista original
    def wrapper(request, *args, **kwargs):
        # hasattr comprueba si existe la relación inversa OneToOne de multi-table inheritance
        if not request.user.is_authenticated or not hasattr(request.user, 'cliente'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def requiere_admin(view_func):
    """
    Permite el acceso solo a usuarios autenticados con rol Administrador.
    Separa explícitamente las vistas de gestión de las vistas de cliente. [OWASP 2.5]
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'administrador'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
