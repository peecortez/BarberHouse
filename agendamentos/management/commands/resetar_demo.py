from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from agendamentos.models import Agendamento, Cliente, EmailEnviado, Profissional

SENHA_DEMO = "barber123"

PROFISSIONAIS_DEMO = [
    {"nome": "Rafael Souza", "email": "rafael@barberhouse.com", "telefone": "(11) 91111-1111", "cpf": "52998224725"},
    {"nome": "Bruno Lima", "email": "bruno@barberhouse.com", "telefone": "(11) 92222-2222", "cpf": "11144477735"},
    {"nome": "Diego Martins", "email": "diego@barberhouse.com", "telefone": "(11) 93333-3333", "cpf": "39053344705"},
    {"nome": "Thiago Alves", "email": "thiago@barberhouse.com", "telefone": "(11) 94444-4444", "cpf": "16899535009"},
]


class Command(BaseCommand):
    help = (
        "Deixa o banco pronto para apresentação: apaga clientes, profissionais, "
        "agendamentos, sessões e o registro de e-mails, e cria 4 profissionais de demonstração. "
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

            for dados in PROFISSIONAIS_DEMO:
                usuario = User.objects.create_user(
                    username=dados["email"],
                    email=dados["email"],
                    password=SENHA_DEMO,
                )
                Profissional.objects.create(usuario=usuario, **dados)

        self.stdout.write(self.style.SUCCESS(
            f"Removidos {agendamentos} agendamentos e os usuários não-admin."
        ))
        self.stdout.write("Profissionais criados (senha de todos: %s):" % SENHA_DEMO)
        for dados in PROFISSIONAIS_DEMO:
            self.stdout.write(f"  {dados['nome']:<15} {dados['email']}")
