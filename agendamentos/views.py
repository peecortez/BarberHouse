from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from .forms import CadastroForm
from .models import Cliente, Profissional
from django.contrib import messages


def cadastro(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data

            usuario = User.objects.create_user(
                username=dados['email'],
                email=dados['email'],
                password=dados['senha']
            )

            if dados['tipo'] == 'cliente':
                Cliente.objects.create(
                    usuario=usuario,
                    nome=dados['nome'],
                    email=dados['email'],
                    telefone=dados['telefone']
                )
            else:
                Profissional.objects.create(
                    usuario=usuario,
                    nome=dados['nome'],
                    email=dados['email'],
                    telefone=dados['telefone']
                )

            messages.success(request, 'Conta criada com sucesso! Faça login para continuar.')
            return redirect('login')
    else:
        form = CadastroForm()

    return render(request, 'cadastro.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        usuario = authenticate(request, username=email, password=senha)
        if usuario is not None:
            login(request, usuario)
            return redirect('home')
    return render(request, 'login.html')


@login_required
def home(request):
    return render(request, 'home.html')
