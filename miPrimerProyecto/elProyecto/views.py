from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login_view(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            messages.error(request, "El correo o la contraseña no coinciden")
            return redirect("login")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")

        messages.error(request, "El correo o la contraseña no coinciden")

    return render(request, "elProyecto/login.html")

    return render(request, "elProyecto/login.html")

def register_view(request):

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        apellidos = request.POST.get("apellidos")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado")
            return redirect("registro")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=nombre,
            last_name=apellidos
        )

        login(request, user)  # login automático
        return redirect("home")

    return render(request, "elProyecto/register.html")

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def home(request):
    return render(request, "elProyecto/home.html")

@login_required
def siames(request):
    return render(request, "elProyecto/siames.html")

@login_required
def creepyNuts(request):
    return render(request, "elProyecto/creepyNuts.html")