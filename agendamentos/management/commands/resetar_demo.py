from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from agendamentos.models import Agendamento, Avaliacao, Cliente, EmailEnviado, Profissional, Servico

SENHA_DEMO = "barber123"

PROFISSIONAIS_DEMO = [
    {"nome": "Rafael Souza", "email": "rafael@barberhouse.com", "telefone": "(11) 91111-1111", "cpf": "52998224725"},
    {"nome": "Bruno Lima", "email": "bruno@barberhouse.com", "telefone": "(11) 92222-2222", "cpf": "11144477735"},
    {"nome": "Diego Martins", "email": "diego@barberhouse.com", "telefone": "(11) 93333-3333", "cpf": "39053344705"},
    {"nome": "Thiago Alves", "email": "thiago@barberhouse.com", "telefone": "(11) 94444-4444", "cpf": "16899535009"},
]

# Avaliacoes de exemplo, para a secao "O que dizem nossos clientes" da home nao
# ficar vazia na apresentacao. "dias" = ha quantos dias foi o atendimento.
AVALIACOES_DEMO = [
    {"cliente": "Lucas Ferreira", "profissional": "rafael@barberhouse.com", "nota": 5, "dias": 2,
     "comentario": "Melhor degradê que já fiz. O Rafael é caprichoso demais e ainda acertou o tempo certinho."},
    {"cliente": "Gabriel Rocha", "profissional": "bruno@barberhouse.com", "nota": 5, "dias": 4,
     "comentario": "Ambiente top, atendimento rápido e a barba ficou perfeita. Já marquei a próxima."},
    {"cliente": "Matheus Costa", "profissional": "diego@barberhouse.com", "nota": 4, "dias": 7,
     "comentario": "Corte muito bem feito. Atrasou uns minutinhos, mas valeu a pena."},
    {"cliente": "Pedro Almeida", "profissional": "thiago@barberhouse.com", "nota": 5, "dias": 11,
     "comentario": "Agendar pelo site foi muito fácil e o Thiago entendeu exatamente o que eu queria."},
    {"cliente": "João Ribeiro", "profissional": "rafael@barberhouse.com", "nota": 5, "dias": 16,
     "comentario": "Saí outro homem. Atendimento atencioso do começo ao fim."},
]


class Command(BaseCommand):
    help = (
        "Deixa o banco pronto para apresentação: apaga clientes, profissionais, "
        "agendamentos, avaliações, sessões e o registro de e-mails, e cria 4 profissionais "
        "de demonstração e, se houver serviço cadastrado, 5 clientes com avaliações de exemplo. "
        "Mantém os superusuários (admin) e os serviços."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            agendamentos = Agendamento.objects.count()
            Agendamento.objects.all().delete()
            Cliente.objects.all().delete()
            Profissional.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            Session.objects.all().delete()
            # Zera o registro de e-mails (e com ele os limites por endereço)
            EmailEnviado.objects.all().delete()

            profissionais = {}
            for dados in PROFISSIONAIS_DEMO:
                profissionais[dados["email"]] = Profissional.objects.create(
                    usuario=self._criar_usuario(dados["email"]), **dados
                )

            servico = Servico.objects.order_by("id").first()
            if servico:
                self._criar_avaliacoes(servico, profissionais)

        self.stdout.write(self.style.SUCCESS(
            f"Removidos {agendamentos} agendamentos e os usuários não-admin."
        ))
        self.stdout.write("Profissionais criados (senha de todos: %s):" % SENHA_DEMO)
        for dados in PROFISSIONAIS_DEMO:
            self.stdout.write(f"  {dados['nome']:<15} {dados['email']}")
        if servico:
            self.stdout.write(f"{len(AVALIACOES_DEMO)} avaliações de exemplo criadas (clientes @cliente.demo).")
        else:
            self.stdout.write(self.style.WARNING(
                "Nenhum serviço cadastrado: as avaliações de exemplo não foram criadas."
            ))

    def _criar_usuario(self, email):
        return User.objects.create_user(username=email, email=email, password=SENHA_DEMO)

    def _criar_avaliacoes(self, servico, profissionais):
        # Criadas direto no banco: nenhum e-mail sai daqui
        hoje = timezone.localdate()
        for item in AVALIACOES_DEMO:
            email = item["cliente"].split()[0].lower().replace("ã", "a") + "@cliente.demo"
            cliente = Cliente.objects.create(
                usuario=self._criar_usuario(email), nome=item["cliente"], email=email, telefone="(11) 90000-0000",
            )
            agendamento = Agendamento.objects.create(
                cliente=cliente,
                profissional=profissionais[item["profissional"]],
                servico=servico,
                data_hora=timezone.make_aware(datetime.combine(hoje - timedelta(days=item["dias"]), time(10, 0))),
                status=Agendamento.Status.CONCLUIDO,
            )
            avaliacao = Avaliacao.objects.create(
                agendamento=agendamento, nota=item["nota"], comentario=item["comentario"],
            )
            # A mais recente aparece primeiro na home
            Avaliacao.objects.filter(pk=avaliacao.pk).update(
                criado_em=agendamento.data_hora + timedelta(hours=2)
            )
