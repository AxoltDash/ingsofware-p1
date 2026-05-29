from django import forms

from .models import Cabana, Parque


class ParqueForm(forms.ModelForm):
    # JSONField se almacena como lista de strings; se presenta como texto separado por comas
    servicios = forms.CharField(
        label='Servicios',
        required=False,
        help_text='Separados por coma, ej: baños, estacionamiento, senderos',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2,
            'placeholder': 'baños, estacionamiento, senderos',
        }),
    )

    class Meta:
        model = Parque
        fields = ['nombre', 'direccion', 'servicios', 'horario',
                  'latitud', 'longitud', 'capacidad_camping']
        widgets = {
            'nombre':            forms.TextInput(attrs={'class': 'form-control'}),
            'direccion':         forms.TextInput(attrs={'class': 'form-control'}),
            'horario':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08:00 – 20:00'}),
            'latitud':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitud':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'capacidad_camping': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # al editar, convertir la lista almacenada en JSON a string legible
        if self.instance and self.instance.pk:
            self.initial['servicios'] = ', '.join(self.instance.servicios or [])

    def clean_servicios(self):
        raw = self.cleaned_data.get('servicios', '')
        if not raw.strip():
            return []
        return [s.strip() for s in raw.split(',') if s.strip()]


class CabanaForm(forms.ModelForm):
    class Meta:
        model = Cabana
        fields = ['nombre', 'capacidad']
        widgets = {
            'nombre':    forms.TextInput(attrs={'class': 'form-control'}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }


class CapacidadCampingForm(forms.Form):
    capacidad_camping = forms.IntegerField(
        label='Nueva capacidad',
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
    )
