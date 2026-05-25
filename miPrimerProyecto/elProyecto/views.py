from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from parques.models import Parque


def home(request):
    return render(request, 'elProyecto/home.html')


def bosques(request):
    parques = Parque.objects.filter(activo=True)
    return render(request, 'elProyecto/bosques.html', {'parques': parques})


@login_required
def siames(request):
    return render(request, 'elProyecto/siames.html')
