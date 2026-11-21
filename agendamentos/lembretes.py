"""Lembretes por e-mail 24h antes do horario.

Quem envia e ``enviar_lembretes_pendentes``. Ele roda de dois jeitos:
- sozinho, numa tarefa em segundo plano enquanto o ``runserver`` esta ligado
  (``iniciar_agendador``, chamado em apps.py);
- na mao: ``python manage.py enviar_lembretes``.
"""
import logging
import os
import sys
import threading
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections
from django.db.models import F
from django.utils import timezone

from .emails import enviar_lembrete
from .models import Agendamento

logger = logging.getLogger(__name__)

JANELA = timedelta(hours=24)
# Quem marcou com menos de um dia de antecedencia acabou de receber o e-mail
# de "horario reservado": lembrete so para quem marcou com mais de 24h.
ANTECEDENCIA_MINIMA = timedelta(hours=24)


def agendamentos_para_lembrar(agora=None):
    agora = agora or timezone.now()
    return Agendamento.objects.filter(
        status__in=[Agendamento.Status.AGENDADO, Agendamento.Status.CONFIRMADO],
        lembrete_enviado_em__isnull=True,
        data_hora__gt=agora,
        data_hora__lte=agora + JANELA,
        criado_em__lte=F('data_hora') - ANTECEDENCIA_MINIMA,
        cliente__usuario__is_active=True,
    ).select_related('cliente', 'profissional', 'servico')


def enviar_lembretes_pendentes():
    """Envia os lembretes devidos. Cada agendamento recebe no maximo um."""
    enviados = 0
    for agendamento in agendamentos_para_lembrar():
        # Marca antes de enviar (update condicional): duas execucoes ao mesmo
        # tempo nunca mandam o mesmo lembrete duas vezes.
        reservado = Agendamento.objects.filter(
            pk=agendamento.pk, lembrete_enviado_em__isnull=True,
        ).update(lembrete_enviado_em=timezone.now())
        if not reservado:
            continue
        if enviar_lembrete(agendamento):
            enviados += 1
        else:
            # Nao saiu (SMTP fora ou teto diario): tenta de novo na proxima rodada
            Agendamento.objects.filter(pk=agendamento.pk).update(lembrete_enviado_em=None)
    return enviados


_agendador_iniciado = False


def _laco(parar, intervalo):
    if parar.wait(15):  # deixa o servidor terminar de subir
        return
    while True:
        try:
            enviados = enviar_lembretes_pendentes()
            if enviados:
                logger.info('%s lembrete(s) enviado(s).', enviados)
        except Exception:
            logger.exception('Erro ao enviar lembretes')
        finally:
            close_old_connections()
        if parar.wait(intervalo):
            return


def iniciar_agendador():
    """Liga a verificacao periodica, so no processo do runserver que atende as paginas."""
    global _agendador_iniciado
    if _agendador_iniciado or not settings.LEMBRETES_AUTOMATICOS:
        return
    if len(sys.argv) < 2 or sys.argv[1] != 'runserver':
        return
    # Com o autoreload o Django sobe dois processos; so o filho (RUN_MAIN) serve as paginas
    if os.environ.get('RUN_MAIN') != 'true' and '--noreload' not in sys.argv:
        return
    _agendador_iniciado = True
    intervalo = max(1, settings.LEMBRETES_INTERVALO_MIN) * 60
    threading.Thread(
        target=_laco, args=(threading.Event(), intervalo), name='lembretes', daemon=True,
    ).start()
