from django import forms
from django.contrib.auth.models import User
from .models import Cliente, Profissional, Servico, Agendamento

class CadastroForm(forms.Form):
    TIPO_CHOICES = [
        ('cliente', 'Cliente'),
        ('profissional', 'Profissional'),
    ]

    tipo = forms.ChoiceField(choices=TIPO_CHOICES, label='Você é:')
    nome = forms.CharField(max_length=100, label='Nome')
    email = forms.EmailField(label='E-mail')
    telefone = forms.CharField(max_length=15, label='Telefone')
    senha = forms.CharField(widget=forms.PasswordInput, label='Senha')

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['cliente', 'profissional', 'servico', 'data_hora']
        widgets = {
            'data_hora': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # If user is a client, only show their client profile
            if hasattr(user, 'cliente'):
                self.fields['cliente'].queryset = Cliente.objects.filter(usuario=user)
                self.fields['cliente'].initial = user.cliente
                self.fields['cliente'].widget = forms.HiddenInput()
            # If user is a professional, only show their professional profile
            elif hasattr(user, 'profissional'):
                self.fields['profissional'].queryset = Profissional.objects.filter(usuario=user)
                self.fields['profissional'].initial = user.profissional
                self.fields['profissional'].widget = forms.HiddenInput()