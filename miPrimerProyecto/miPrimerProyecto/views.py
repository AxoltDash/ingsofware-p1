from django.shortcuts import render


def error_404(request, exception):
    """[OWASP 2.7] Página 404 — mensaje genérico, sin exponer rutas internas."""
    return render(request, '404.html', status=404)


def error_500(request):
    """[OWASP 2.7] Página 500 — template standalone, no hereda base.html para evitar
    que un error en el renderizado del base cause recursión o página en blanco."""
    return render(request, '500.html', status=500)
