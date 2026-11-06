import re

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import Cliente, Profissional, Servico, Agendamento

def cpf_valido(cpf):
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            return False
    return True


class CadastroForm(forms.Form):
    TIPO_CHOICES = [
        ('cliente', 'Cliente'),
        ('profissional', 'Profissional'),
    ]

    tipo = forms.ChoiceField(choices=TIPO_CHOICES, label='Você é:')
    nome = forms.CharField(max_length=100, label='Nome')
    email = forms.EmailField(label='E-mail')
    telefone = forms.CharField(max_length=15, label='Telefone')
    cpf = forms.CharField(max_length=14, label='CPF')
    senha = forms.CharField(widget=forms.PasswordInput, label='Senha')
    senha_confirmacao = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmar Senha",
    )

    def clean(self):
        dados = super().clean()
        senha = dados.get("senha")
        confirmacao = dados.get("senha_confirmacao")
        if senha and confirmacao and senha != confirmacao:
            self.add_error(
                "senha_confirmacao",
                "As senhas n\u00e3o coincidem.",
            )
        return dados

    def clean_cpf(self):
        cpf = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if not cpf_valido(cpf):
            raise ValidationError("CPF inválido.")
        if (
            Cliente.objects.filter(cpf=cpf).exists()
            or Profissional.objects.filter(cpf=cpf).exists()
        ):
            raise ValidationError("Este CPF já está cadastrado.")
        return cpf

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if (
            User.objects.filter(username__iexact=email).exists()
            or Cliente.objects.filter(email__iexact=email).exists()
            or Profissional.objects.filter(email__iexact=email).exists()
        ):
            raise ValidationError("Este e-mail ja esta cadastrado. Entre ou use outro.")
        return email

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