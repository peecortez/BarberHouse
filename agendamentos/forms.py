import re

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.urls import reverse
from .emails import bloqueado_para_destinatario, enviar
from .models import Avaliacao, Cliente, Profissional, Servico, Agendamento

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

class RecuperarSenhaForm(PasswordResetForm):
    """O formulario de "esqueci a senha" do Django, enviando pelo nosso e-mail.

    Passa pelo teto diario e pelo limite por endereco (1 por minuto, 5 por dia),
    para ninguem usar a tela para disparar e-mails em massa.
    """

    def get_users(self, email):
        # A mesma conta que o login usa (username = e-mail). O Django procura pelo
        # campo "email", e um admin com o mesmo e-mail acabava recebendo o link.
        contas = User.objects.filter(username__iexact=email, is_active=True)
        return (u for u in contas if u.has_usable_password())

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        if bloqueado_para_destinatario(to_email, 'redefinir_senha'):
            return
        usuario = context['user']
        perfil = getattr(usuario, 'cliente', None) or getattr(usuario, 'profissional', None)
        caminho = reverse('password_reset_confirm', kwargs={'uidb64': context['uid'], 'token': context['token']})
        enviar('redefinir_senha', to_email, 'Redefina sua senha na BarberHouse', 'redefinir_senha', {
            'nome': perfil.nome.split()[0] if perfil and perfil.nome else '',
            'link': f"{context['protocol']}://{context['domain']}{caminho}",
        })


class AvaliacaoForm(forms.ModelForm):
    nota = forms.TypedChoiceField(
        choices=[(n, n) for n in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={'required': 'Escolha de 1 a 5 estrelas.'},
    )
    comentario = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    class Meta:
        model = Avaliacao
        fields = ['nota', 'comentario']


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