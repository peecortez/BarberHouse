import json
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Agendamento, Cliente, Profissional, Servico

BASE = Path(__file__).parent
JS = BASE / "static" / "agendamentos" / "menu.js"
TEMPLATES = BASE / "templates"


class FluxoAgendamentoTest(TestCase):
    def setUp(self):
        u = User.objects.create_user("cli@x.com", "cli@x.com", "senha123")
        Cliente.objects.create(usuario=u, nome="Cli", email="cli@x.com", telefone="1")
        p = User.objects.create_user("bar@x.com", "bar@x.com", "senha123")
        self.prof = Profissional.objects.create(usuario=p, nome="Barbeiro", email="bar@x.com", telefone="2")
        self.servico = Servico.objects.create(nome="Corte", duracao_minutos=30, preco=40)
        self.amanha = (date.today() + timedelta(days=1)).isoformat()

    def logar(self, email):
        self.assertTrue(self.client.login(username=email, password="senha123"))

    def test_anonimo_vai_pro_login(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_anonimo_nao_agenda(self):
        r = self.client.post(reverse("agendar_servico"), "{}", content_type="application/json")
        self.assertEqual(r.status_code, 302)  # @login_required

    def test_agenda_cliente_carrega_menu_js(self):
        self.logar("cli@x.com")
        self.assertContains(self.client.get(reverse("agenda_cliente")), "menu.js")

    def test_gerenciar_agenda_carrega_menu_js(self):
        self.logar("bar@x.com")
        self.assertContains(self.client.get(reverse("gerenciar_agenda")), "menu.js")

    def test_profissional_abre_e_fecha_agenda(self):
        self.logar("bar@x.com")
        r = self.client.post(reverse("toggle_agenda_aberta"))
        self.assertEqual(r.status_code, 200)
        self.prof.refresh_from_db()
        self.assertFalse(self.prof.agenda_aberta)

    def test_menu_js_navega_e_nao_manda_segundos(self):
        js = JS.read_text(encoding="utf-8")
        for rota in ("/agenda-cliente/", "/meus-agendamentos/", "/noticias/", "/mais/"):
            self.assertIn(rota, js)
        self.assertNotIn("${horario}:00", js)

    def test_agendar_ponta_a_ponta(self):
        self.logar("cli@x.com")
        url = f"/horarios-disponiveis/?servico={self.servico.id}&profissional={self.prof.id}&data={self.amanha}"
        horarios = self.client.get(url).json()["horarios"]
        self.assertTrue(horarios)
        corpo = {"servico_id": self.servico.id, "profissional_id": self.prof.id,
                 "data_hora": f"{self.amanha}T{horarios[0]}"}
        r = self.client.post(reverse("agendar_servico"), json.dumps(corpo), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        depois = self.client.get(url).json()["horarios"]  # com agendamento já existente
        self.assertNotIn(horarios[0], depois)


class BaseComPerfis(TestCase):
    def setUp(self):
        u = User.objects.create_user("cli@x.com", "cli@x.com", "senha123")
        self.cliente = Cliente.objects.create(usuario=u, nome="Cli", email="cli@x.com", telefone="1")
        p = User.objects.create_user("bar@x.com", "bar@x.com", "senha123")
        self.prof = Profissional.objects.create(usuario=p, nome="Barbeiro", email="bar@x.com", telefone="2")
        p2 = User.objects.create_user("bar2@x.com", "bar2@x.com", "senha123")
        self.prof2 = Profissional.objects.create(usuario=p2, nome="Outro", email="bar2@x.com", telefone="3")
        self.servico = Servico.objects.create(nome="Corte", duracao_minutos=30, preco=40)
        amanha = date.today() + timedelta(days=1)
        self.amanha = amanha.isoformat()
        self.agendamento = Agendamento.objects.create(
            cliente=self.cliente, profissional=self.prof, servico=self.servico,
            data_hora=timezone.make_aware(datetime.combine(amanha, time(10, 0))),
        )

    def logar(self, email):
        self.client.logout()
        self.assertTrue(self.client.login(username=email, password="senha123"))

    def acao(self, acao, agendamento=None):
        ag = agendamento or self.agendamento
        return self.client.post(reverse("atualizar_status", args=[ag.id]),
                                json.dumps({"acao": acao}), content_type="application/json")

    def horarios(self):
        url = f"/horarios-disponiveis/?servico={self.servico.id}&profissional={self.prof.id}&data={self.amanha}"
        return self.client.get(url).json()["horarios"]


class MenuPorPerfilTest(BaseComPerfis):
    def test_profissional_ve_minha_agenda_e_nao_agendar(self):
        self.logar("bar@x.com")
        html = self.client.get("/").content.decode()
        self.assertIn("Minha Agenda", html)
        self.assertNotIn('data-pagina="agenda"', html)
        self.assertNotIn("Meus agendamentos", html)

    def test_cliente_ve_agendar_e_nao_minha_agenda(self):
        self.logar("cli@x.com")
        html = self.client.get("/").content.decode()
        self.assertIn('data-pagina="agenda"', html)
        self.assertIn("Meus agendamentos", html)
        self.assertNotIn("Minha Agenda", html)

    def test_profissional_em_meus_agendamentos_vai_pra_minha_agenda(self):
        self.logar("bar@x.com")
        r = self.client.get(reverse("meus_agendamentos"))
        self.assertRedirects(r, reverse("gerenciar_agenda"))


class LogoutEVoltarTest(BaseComPerfis):
    def test_logout_por_post_volta_pro_login(self):
        self.logar("cli@x.com")
        r = self.client.post(reverse("logout"))
        self.assertRedirects(r, reverse("login"), fetch_redirect_response=False)
        self.assertEqual(self.client.get("/").status_code, 302)  # sessão encerrada

    def test_logout_por_get_nao_desloga(self):
        self.logar("cli@x.com")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_telas_tem_voltar_e_sair(self):
        self.logar("cli@x.com")
        for nome in ("agenda_cliente", "meus_agendamentos", "noticias", "mais"):
            html = self.client.get(reverse(nome)).content.decode()
            self.assertIn("Voltar", html, nome)
            self.assertIn(f'action="{reverse("logout")}"', html, nome)
        self.logar("bar@x.com")
        html = self.client.get(reverse("gerenciar_agenda")).content.decode()
        self.assertIn("Voltar", html)
        self.assertIn(f'action="{reverse("logout")}"', html)

    def test_menu_principal_tem_sair(self):
        self.logar("cli@x.com")
        self.assertIn(f'action="{reverse("logout")}"', self.client.get("/").content.decode())


class StatusAgendamentoTest(BaseComPerfis):
    def test_profissional_confirma_e_conclui(self):
        self.logar("bar@x.com")
        self.assertEqual(self.acao("confirmar").status_code, 200)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, "CONFIRMADO")
        self.assertEqual(self.acao("concluir").status_code, 200)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, "CONCLUIDO")

    def test_cliente_nao_confirma_nem_conclui(self):
        self.logar("cli@x.com")
        self.assertEqual(self.acao("confirmar").status_code, 403)
        self.assertEqual(self.acao("concluir").status_code, 403)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, "AGENDADO")

    def test_outro_profissional_nao_mexe(self):
        self.logar("bar2@x.com")
        self.assertEqual(self.acao("cancelar").status_code, 403)

    def test_cliente_cancela_o_proprio_e_horario_volta(self):
        self.logar("cli@x.com")
        self.assertNotIn("10:00", self.horarios())
        self.assertEqual(self.acao("cancelar").status_code, 200)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, "CANCELADO")
        self.assertIn("10:00", self.horarios())

    def test_nao_age_sobre_agendamento_ja_concluido(self):
        self.logar("bar@x.com")
        self.acao("concluir")
        self.assertEqual(self.acao("cancelar").status_code, 409)

    def test_horario_cancelado_pode_ser_reagendado(self):
        self.logar("bar@x.com")
        self.acao("cancelar")
        self.logar("cli@x.com")
        corpo = {"servico_id": self.servico.id, "profissional_id": self.prof.id, "data_hora": f"{self.amanha}T10:00"}
        r = self.client.post(reverse("agendar_servico"), json.dumps(corpo), content_type="application/json")
        self.assertEqual(r.status_code, 200)

    def test_minha_agenda_mostra_botoes_de_acao(self):
        self.logar("bar@x.com")
        html = self.client.get(reverse("gerenciar_agenda")).content.decode()
        for acao in ("confirmar", "concluir", "cancelar"):
            self.assertIn(f'data-acao="{acao}"', html)


class VersaoDoStaticTest(BaseComPerfis):
    def test_tag_gera_versao_automatica(self):
        from .templatetags.versao_static import static_v
        self.assertRegex(static_v("agendamentos/menu.js"), r"/static/agendamentos/menu\.js\?v=\d+$")
        self.assertEqual(static_v("agendamentos/nao_existe.js"), "/static/agendamentos/nao_existe.js")

    def test_paginas_usam_a_versao_automatica(self):
        self.logar("cli@x.com")
        html = self.client.get("/").content.decode()
        self.assertRegex(html, r"menu\.js\?v=\d+")
        self.assertRegex(html, r"barbearia\.css\?v=\d+")

    def test_nenhum_template_tem_versao_na_mao(self):
        for arquivo in TEMPLATES.glob("*.html"):
            texto = arquivo.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"static '[^']+\.(js|css)' %\}\?v=", texto), arquivo.name)