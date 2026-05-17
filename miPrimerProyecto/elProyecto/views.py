from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .models import Parque

def home(request):
    return render(request, "elProyecto/home.html")



def bosques(request):
    parques = Parque.objects.all()
    return render(request, 'elProyecto/bosques.html', {
        'parques': parques,
    })

@login_required
def siames(request):
    return render(request, "elProyecto/siames.html")

@login_required
def creepyNuts(request):
    return render(request, "elProyecto/creepyNuts.html")

def registro(request):

    data = {
        'form': CustomUserCreationForm()
    }

    if request.method == "POST":
        formulario = CustomUserCreationForm(data=request.POST)

        if formulario.is_valid():
            usuario = formulario.save()

            user = authenticate(
                username=formulario.cleaned_data["username"],
                password=formulario.cleaned_data["password1"]
            )

            login(request, user)

            return redirect("home")

        data["form"] = formulario

    return render(request, 'registration/registro.html', data)