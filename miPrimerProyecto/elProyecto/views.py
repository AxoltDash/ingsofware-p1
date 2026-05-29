from django.shortcuts import render

from parques.models import Parque
from usuarios.decorators import requiere_cliente


def home(request):
    return render(request, 'elProyecto/home.html')


def bosques(request):
    parques = Parque.objects.filter(activo=True)
    return render(request, 'elProyecto/bosques.html', {'parques': parques})


@requiere_cliente  # reemplaza @login_required: ahora solo clientes pueden entrar, no admins
def siames(request):
    return render(request, 'elProyecto/siames.html')
