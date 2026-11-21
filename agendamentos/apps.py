from django.apps import AppConfig


class AgendamentosConfig(AppConfig):
    name = 'agendamentos'

    def ready(self):
        # Lembretes de 24h: verificacao em segundo plano enquanto o runserver roda
        from .lembretes import iniciar_agendador
        iniciar_agendador()
