from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=15)

 
class Profissional(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=15)
    agenda_aberta = models.BooleanField(default=True)


class Servico(models.Model):
    nome = models.CharField(max_length=100)
    duracao_minutos = models.IntegerField()
    preco = models.DecimalField(max_digits=6, decimal_places=2)


class Agendamento(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
    data_hora = models.DateTimeField()
    criado_em = models.DateTimeField(auto_now_add=True)
