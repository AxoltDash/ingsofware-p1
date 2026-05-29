from django import forms

from .models import TipoVisita


class ReservacionPaso1Form(forms.Form):
    """Paso 1: fechas y tipo de visita. Para camping también recoge número de personas."""
    fecha_inicio = forms.DateField(
        label='Fecha de llegada',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_termino = forms.DateField(
        label='Fecha de salida',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    tipo_visita = forms.ChoiceField(
        label='Tipo de visita',
        choices=TipoVisita.choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    # solo obligatorio cuando tipo_visita == CAMPING; el template lo muestra/oculta con JS
    numero_personas = forms.IntegerField(
        label='Número de personas',
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
    )

    def __init__(self, parque, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not parque.tiene_cabanas:
            self.fields['tipo_visita'].choices = [
                (TipoVisita.CAMPING, TipoVisita.CAMPING.label)
            ]

    def clean(self):
        cleaned = super().clean()
        fi = cleaned.get('fecha_inicio')
        ft = cleaned.get('fecha_termino')
        if fi and ft and fi > ft:
            raise forms.ValidationError(
                "La fecha de salida no puede ser anterior a la fecha de llegada."
            )
        tipo = cleaned.get('tipo_visita')
        if tipo == TipoVisita.CAMPING and not cleaned.get('numero_personas'):
            self.add_error('numero_personas', 'Indica cuántas personas asistirán.')
        return cleaned


class ReservacionCabanaForm(forms.Form):
    """Paso 2 (cabaña): selección de cabaña disponible y número de personas."""
    cabana = forms.ModelChoiceField(
        queryset=None,
        label='Cabaña disponible',
        empty_label='— Selecciona una cabaña —',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    numero_personas = forms.IntegerField(
        label='Número de personas',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
    )

    def __init__(self, cabanas_qs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cabana'].queryset = cabanas_qs
