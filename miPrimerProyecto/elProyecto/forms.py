from django.contrib.auth.forms import UserCreationForm
from usuarios.models import Cliente


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = Cliente
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']
