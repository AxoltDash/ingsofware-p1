from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from parques.models import Parque
from .forms import CustomUserCreationForm


def home(request):
    return render(request, "elProyecto/home.html")


def bosques(request):
    parques = Parque.objects.filter(activo=True)
    return render(request, 'elProyecto/bosques.html', {'parques': parques})


@login_required
def siames(request):
    return render(request, "elProyecto/siames.html")


@login_required
def creepyNuts(request):
    return render(request, "elProyecto/creepyNuts.html")


def registro(request):
    data = {'form': CustomUserCreationForm()}

    if request.method == "POST":
        formulario = CustomUserCreationForm(data=request.POST)
        if formulario.is_valid():
            user = formulario.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect("home")
        data["form"] = formulario

    return render(request, 'registration/registro.html', data)
