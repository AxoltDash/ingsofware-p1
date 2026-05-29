from django.http import JsonResponse

from .models import Parque


def api_marcadores(request):
    """RF-02: coordenadas de parques activos para el mapa interactivo."""
    parques = Parque.objects.filter(activo=True).values(
        'id', 'nombre', 'latitud', 'longitud', 'direccion'
    )
    return JsonResponse(list(parques), safe=False)
