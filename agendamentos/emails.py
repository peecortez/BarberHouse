"""Envio de e-mails do sistema, com travas contra abuso e gasto.

Todo e-mail passa por ``enviar``, que:
- respeita o teto diario (settings.EMAIL_LIMITE_DIARIO);
- registra o envio em EmailEnviado (base do teto e do limite por destinatario);
- nunca derruba a tela: se o SMTP falhar, registra no log e segue.

Os e-mails so vao para o endereco do proprio usuario cadastrado: nao existe
nenhuma tela onde se digite um destinatario qualquer.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import Agendamento, EmailEnviado

logger = logging.getLogger(__name__)

SALT_CONFIRMACAO = 'agendamentos.confirmar-email'
VALIDADE_CONFIRMACAO = 60 * 60 * 24  # 24h

# Para e-mails que qualquer pessoa pode pedir (reenviar confirmacao, redefinir senha)
INTERVALO_MINIMO = timedelta(seconds=60)
MAXIMO_POR_DIA_POR_DESTINATARIO = 5


def _inicio_do_dia():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def limite_diario_atingido():
    enviados = EmailEnviado.objects.filter(enviado_em__gte=_inicio_do_dia(), sucesso=True).count()
    return enviados >= settings.EMAIL_LIMITE_DIARIO


def bloqueado_para_destinatario(destinatario, tipo):
    """True se esse endereco ja recebeu esse tipo de e-mail ha menos de 1 min ou 5 vezes hoje."""
    recentes = EmailEnviado.objects.filter(destinatario__iexact=destinatario, tipo=tipo)
    if recentes.filter(enviado_em__gte=timezone.now() - INTERVALO_MINIMO).exists():
        return True
    return recentes.filter(enviado_em__gte=_inicio_do_dia()).count() >= MAXIMO_POR_DIA_POR_DESTINATARIO


def url_absoluta(request, caminho):
    """Link completo: usa o endereco da requisicao (localhost ou tunel) ou o SITE_URL."""
    if request is not None:
        return request.build_absolute_uri(caminho)
    return settings.SITE_URL + caminho


def enviar(tipo, destinatario, assunto, template, contexto):
    """Monta o e-mail (texto + HTML) e envia. Retorna True se saiu."""
    if not destinatario:
        return False
    if limite_diario_atingido():
        logger.warning('Teto diario de e-mails atingido (%s). Nao enviado: %s para %s',
                       settings.EMAIL_LIMITE_DIARIO, tipo, destinatario)
        return False

    contexto = {**contexto, 'assunto': assunto}
    texto = render_to_string(f'emails/{template}.txt', contexto)
    html = render_to_string(f'emails/{template}.html', contexto)
    mensagem = EmailMultiAlternatives(assunto, texto, settings.DEFAULT_FROM_EMAIL, [destinatario])
    mensagem.attach_alternative(html, 'text/html')
    try:
        mensagem.send()
    except Exception:
        logger.exception('Falha ao enviar e-mail %s para %s', tipo, destinatario)
        EmailEnviado.objects.create(destinatario=destinatario, tipo=tipo, assunto=assunto, sucesso=False)
        return False
    EmailEnviado.objects.create(destinatario=destinatario, tipo=tipo, assunto=assunto)
    return True


# ---------------------------------------------------------------- cadastro

def gerar_token_confirmacao(usuario):
    return signing.dumps(usuario.pk, salt=SALT_CONFIRMACAO)


def ler_token_confirmacao(token):
    """Devolve o id do usuario do link, ou None se o link for invalido ou tiver expirado."""
    try:
        return signing.loads(token, salt=SALT_CONFIRMACAO, max_age=VALIDADE_CONFIRMACAO)
    except signing.BadSignature:  # inclui SignatureExpired
        return None


def enviar_confirmacao_cadastro(request, usuario, nome):
    link = url_absoluta(request, reverse('confirmar_email', args=[gerar_token_confirmacao(usuario)]))
    return enviar(
        'confirmacao', usuario.email, 'Confirme seu e-mail na BarberHouse', 'confirmar_cadastro',
        {'nome': nome.split()[0] if nome else '', 'link': link},
    )


# ------------------------------------------------------------ agendamentos

def _nome_cliente(agendamento):
    return agendamento.cliente.nome.split()[0] if agendamento.cliente.nome else ''


def enviar_aviso_agendamento(request, agendamento, evento):
    """Avisa o cliente sobre o agendamento. evento: criado, confirmado, cancelado, concluido."""
    Status = Agendamento.Status
    contexto = {'agendamento': agendamento, 'nome': _nome_cliente(agendamento), 'evento': evento}

    if evento == 'criado':
        assunto = 'Seu horário está reservado'
        contexto['botao'] = ('Ver meus agendamentos', reverse('meus_agendamentos'))
    elif evento == 'confirmado':
        assunto = 'Seu horário foi confirmado'
        contexto['botao'] = ('Ver meus agendamentos', reverse('meus_agendamentos'))
    elif evento == 'cancelado':
        assunto = 'Seu agendamento foi cancelado'
        contexto['cancelado_pelo_profissional'] = (
            agendamento.cancelado_por == Agendamento.CanceladoPor.PROFISSIONAL
        )
        contexto['botao'] = ('Agendar outro horário', reverse('agenda_cliente'))
    elif evento == 'concluido':
        assunto = 'Como foi seu atendimento?'
        contexto['botao'] = ('Avaliar atendimento', reverse('avaliar_atendimento', args=[agendamento.id]))
    else:
        raise ValueError(f'Evento desconhecido: {evento}')

    if agendamento.status == Status.CANCELADO and evento != 'cancelado':
        return False

    texto_botao, caminho = contexto['botao']
    contexto['botao'] = {'texto': texto_botao, 'url': url_absoluta(request, caminho)}
    return enviar(f'agendamento_{evento}', agendamento.cliente.email, assunto, 'agendamento', contexto)


def enviar_lembrete(agendamento):
    inicio = timezone.localtime(agendamento.data_hora)
    quando = 'hoje' if inicio.date() == timezone.localdate() else 'amanhã'
    contexto = {
        'agendamento': agendamento,
        'nome': _nome_cliente(agendamento),
        'evento': 'lembrete',
        'quando': quando,
        'botao': {'texto': 'Ver meus agendamentos', 'url': url_absoluta(None, reverse('meus_agendamentos'))},
    }
    assunto = f'Lembrete: seu horário é {quando} às {inicio:%H:%M}'
    return enviar('lembrete', agendamento.cliente.email, assunto, 'agendamento', contexto)
