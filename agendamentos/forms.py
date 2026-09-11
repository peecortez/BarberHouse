from django import forms
from django.contrib.auth.models import User

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