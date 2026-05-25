from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, SetPasswordForm
from django import forms

from .models import Cliente


class RegistroClienteForm(UserCreationForm):
    class Meta:
        model = Cliente
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True   # se requiere nombre para el registro
        self.fields['last_name'].required = True
        self.fields['email'].widget.attrs.update({'placeholder': 'tu@correo.com'})


class LoginForm(AuthenticationForm):
    # AuthenticationForm usa USERNAME_FIELD='email' automáticamente para la búsqueda en BD
    # solo ajustamos la etiqueta y placeholder para que sea en español
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Correo electrónico'
        self.fields['username'].widget.attrs.update({'placeholder': 'tu@correo.com'})
        self.fields['password'].widget.attrs.update({'placeholder': '••••••••'})


class RecuperacionForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'placeholder': 'tu@correo.com'})
    )


class RestablecerForm(SetPasswordForm):
    # SetPasswordForm ya valida que las dos contraseñas coincidan y aplica AUTH_PASSWORD_VALIDATORS
    pass
