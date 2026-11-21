from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.
class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=15)
    cpf = models.CharField(max_length=11, unique=True, null=True, blank=True)
    cupom_resgatado_em = models.DateTimeField(null=True, blank=True)

    @property
    def cupom_resgatado(self):
        return self.cupom_resgatado_em is not None

    @property
    def cupom_disponivel(self):
        return bool(self.cpf) and not self.cupom_resgatado

    @property
    def codigo_promocao(self):
        if not self.cpf:
            return None
        return f"BARBER15OFF{self.cpf[-3:]}"


class Profissional(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=15)
    cpf = models.CharField(max_length=11, unique=True, null=True, blank=True)
    agenda_aberta = models.BooleanField(default=True)


class Servico(models.Model):
    nome = models.CharField(max_length=100)
    duracao_minutos = models.IntegerField()
    preco = models.DecimalField(max_digits=6, decimal_places=2)


class Agendamento(models.Model):
    class CanceladoPor(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente'
        PROFISSIONAL = 'PROFISSIONAL', 'Profissional'

    class Status(models.TextChoices):
        AGENDADO = 'AGENDADO', 'Agendado'
        CONFIRMADO = 'CONFIRMADO', 'Confirmado'
        CONCLUIDO = 'CONCLUIDO', 'Concluído'
        CANCELADO = 'CANCELADO', 'Cancelado'

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
    data_hora = models.DateTimeField()
    criado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.AGENDADO,
    )
    cupom_aplicado = models.BooleanField(default=False)
    cancelado_por = models.CharField(
        max_length=13,
        choices=CanceladoPor.choices,
        blank=True,
        default='',
    )
    # Marcado ao enviar o lembrete de 24h, para nunca mandar duas vezes
    lembrete_enviado_em = models.DateTimeField(null=True, blank=True)


class Avaliacao(models.Model):
    """Nota de 1 a 5 que o cliente da a um atendimento concluido (uma por agendamento)."""

    agendamento = models.OneToOneField(Agendamento, on_delete=models.CASCADE, related_name='avaliacao')
    nota = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'avaliação'
        verbose_name_plural = 'avaliações'

    def __str__(self):
        return f'{self.nota}/5 - {self.agendamento}'


class EmailEnviado(models.Model):
    """Registro de cada e-mail: serve para o teto diario e o limite por destinatario."""

    destinatario = models.EmailField()
    tipo = models.CharField(max_length=30)
    assunto = models.CharField(max_length=200)
    enviado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    sucesso = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'e-mail enviado'
        verbose_name_plural = 'e-mails enviados'
        ordering = ['-enviado_em']

    def __str__(self):
        return f'{self.tipo} -> {self.destinatario}'
