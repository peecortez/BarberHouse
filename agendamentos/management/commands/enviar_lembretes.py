from django.core.management.base import BaseCommand

from agendamentos.lembretes import enviar_lembretes_pendentes


class Command(BaseCommand):
    help = (
        "Envia os lembretes por e-mail dos horários das próximas 24h "
        "(cada agendamento recebe no máximo um). Com o runserver ligado isso já "
        "acontece sozinho; este comando serve para rodar na mão ou pelo Agendador de Tarefas."
    )

    def handle(self, *args, **options):
        enviados = enviar_lembretes_pendentes()
        self.stdout.write(self.style.SUCCESS(f"{enviados} lembrete(s) enviado(s)."))
