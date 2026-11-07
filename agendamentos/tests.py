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

    def test_menu_navega_e_js_nao_manda_segundos(self):
        # A navegacao agora e feita por links nos templates (home + barra fixa)
        self.logar("cli@x.com")
        html = self.client.get("/").content.decode()
        for rota in ("/agenda-cliente/", "/meus-agendamentos/", "/noticias/", "/mais/"):
            self.assertIn(f'href="{rota}"', html)
        js = JS.read_text(encoding="utf-8")
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
        self.assertIn(f'href="{reverse("gerenciar_agenda")}"', html)
        self.assertIn("minha agenda", html.lower())
        self.assertNotIn(f'href="{reverse("agenda_cliente")}"', html)
        self.assertNotIn("Meus agendamentos", html)

    def test_cliente_ve_agendar_e_nao_minha_agenda(self):
        self.logar("cli@x.com")
        html = self.client.get("/").content.decode()
        self.assertIn(f'href="{reverse("agenda_cliente")}"', html)
        self.assertIn("Meus agendamentos", html)
        self.assertNotIn(f'href="{reverse("gerenciar_agenda")}"', html)
        self.assertNotIn("minha agenda", html.lower())

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
        # A barra fixa (base_app.html) leva de volta ao inicio e tem o botao Sair
        voltar = f'href="{reverse("home")}"'
        self.logar("cli@x.com")
        for nome in ("agenda_cliente", "meus_agendamentos", "noticias", "mais"):
            html = self.client.get(reverse(nome)).content.decode()
            self.assertIn(voltar, html, nome)
            self.assertIn(f'action="{reverse("logout")}"', html, nome)
        self.logar("bar@x.com")
        html = self.client.get(reverse("gerenciar_agenda")).content.decode()
        self.assertIn(voltar, html)
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

class CadastroCpfTests(TestCase):
    def dados(self, **extra):
        base = {
            "tipo": "cliente", "nome": "Novo", "email": "novo@x.com",
            "telefone": "11999999999", "cpf": "529.982.247-25",
            "senha": "Senha123!", "senha_confirmacao": "Senha123!",
        }
        base.update(extra)
        return base

    def test_cadastro_salva_cpf_somente_digitos(self):
        resp = self.client.post("/cadastro/", self.dados())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Cliente.objects.get().cpf, "52998224725")

    def test_cpf_invalido_e_recusado(self):
        for cpf in ("111.111.111-11", "529.982.247-24", "123"):
            resp = self.client.post("/cadastro/", self.dados(cpf=cpf))
            self.assertEqual(resp.status_code, 200)
            self.assertIn("cpf", resp.context["form"].errors)
        self.assertEqual(Cliente.objects.count(), 0)

    def test_cpf_duplicado_e_recusado(self):
        self.client.post("/cadastro/", self.dados())
        resp = self.client.post(
            "/cadastro/", self.dados(email="outro@x.com", tipo="profissional")
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("cpf", resp.context["form"].errors)
        self.assertEqual(Profissional.objects.count(), 0)


class PromocaoNoticiasTests(TestCase):
    def test_cliente_ve_codigo_com_ultimos_3_digitos_do_cpf(self):
        u = User.objects.create_user("c@x.com", "c@x.com", "senha123")
        Cliente.objects.create(usuario=u, nome="C", email="c@x.com", telefone="1", cpf="52998224725")
        self.client.login(username="c@x.com", password="senha123")
        resp = self.client.get(reverse("noticias"))
        self.assertContains(resp, "BARBER15OFF725")
        self.assertNotContains(resp, "52998224725")

    def test_anonimo_nao_ve_codigo(self):
        resp = self.client.get(reverse("noticias"))
        self.assertNotContains(resp, "BARBER15OFF")
        self.assertContains(resp, "15%")


class ResgateCupomTests(TestCase):
    def setUp(self):
        u = User.objects.create_user("c@x.com", "c@x.com", "senha123")
        self.cliente = Cliente.objects.create(usuario=u, nome="C", email="c@x.com", telefone="1", cpf="52998224725")
        p = User.objects.create_user("p@x.com", "p@x.com", "senha123")
        self.prof = Profissional.objects.create(usuario=p, nome="P", email="p@x.com", telefone="2")
        self.servico = Servico.objects.create(nome="Corte", duracao_minutos=30, preco=40)

    def agendamento(self):
        return Agendamento.objects.create(
            cliente=self.cliente, profissional=self.prof, servico=self.servico,
            data_hora=timezone.now() + timedelta(days=1),
        )

    def concluir(self, ag, **extra):
        self.client.login(username="p@x.com", password="senha123")
        return self.client.post(
            reverse("atualizar_status", args=[ag.id]),
            data=json.dumps({"acao": "concluir", **extra}),
            content_type="application/json",
        )

    def test_concluir_com_cupom_resgata_e_bloqueia_reuso(self):
        ag = self.agendamento()
        self.assertEqual(self.concluir(ag, cupom=True).status_code, 200)
        self.cliente.refresh_from_db()
        ag.refresh_from_db()
        self.assertTrue(self.cliente.cupom_resgatado)
        self.assertTrue(ag.cupom_aplicado)
        self.assertEqual(ag.status, Agendamento.Status.CONCLUIDO)

        ag2 = self.agendamento()
        resp = self.concluir(ag2, cupom=True)
        self.assertEqual(resp.status_code, 409)
        ag2.refresh_from_db()
        self.assertEqual(ag2.status, Agendamento.Status.AGENDADO)
        self.assertFalse(ag2.cupom_aplicado)

    def test_concluir_sem_cupom_nao_resgata(self):
        ag = self.agendamento()
        self.assertEqual(self.concluir(ag).status_code, 200)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.cupom_resgatado)

    def test_cliente_nao_pode_resgatar_o_proprio_cupom(self):
        ag = self.agendamento()
        self.client.login(username="c@x.com", password="senha123")
        resp = self.client.post(
            reverse("atualizar_status", args=[ag.id]),
            data=json.dumps({"acao": "concluir", "cupom": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.cupom_resgatado)

    def test_noticias_mostra_cupom_ja_resgatado(self):
        self.cliente.cupom_resgatado_em = timezone.now()
        self.cliente.save()
        self.client.login(username="c@x.com", password="senha123")
        resp = self.client.get(reverse("noticias"))
        self.assertContains(resp, "Cupom já resgatado")
        self.assertNotContains(resp, "BARBER15OFF725")


class MensagensTests(TestCase):
    def setUp(self):
        User.objects.create_user("m@x.com", "m@x.com", "senha123")

    def test_mensagem_de_login_aparece_na_tela_seguinte(self):
        resp = self.client.post(reverse("login"), {"email": "m@x.com", "senha": "senha123"}, follow=True)
        self.assertContains(resp, "Login realizado com sucesso")

    def test_notificacao_tem_botao_de_fechar(self):
        resp = self.client.post(reverse("login"), {"email": "m@x.com", "senha": "senha123"}, follow=True)
        self.assertContains(resp, 'class="toast-fechar"')
        self.assertContains(resp, 'aria-label="Fechar notificação"')

    def test_notificacao_dura_6_segundos(self):
        css = (BASE / "static" / "agendamentos" / "barbearia.css").read_text(encoding="utf-8")
        self.assertIn("--toast-duracao: 6s;", css)

    def test_mensagem_de_login_nao_reaparece_apos_logout(self):
        self.client.post(reverse("login"), {"email": "m@x.com", "senha": "senha123"})
        resp = self.client.post(reverse("logout"), follow=True)
        self.assertNotContains(resp, "Login realizado com sucesso")

    def test_mensagem_nao_fica_pendente_ao_navegar_entre_paginas(self):
        self.client.post(reverse("login"), {"email": "m@x.com", "senha": "senha123"})
        for nome in ("home", "noticias", "mais"):
            resp = self.client.get(reverse(nome))
            self.assertEqual(resp.status_code, 200)
        resp = self.client.post(reverse("logout"), follow=True)
        self.assertNotContains(resp, "Login realizado com sucesso")


class LogoTests(BaseComPerfis):
    def test_logo_no_login_com_slogan(self):
        resp = self.client.get(reverse("login"))
        self.assertContains(resp, 'class="logo logo-auth"')
        self.assertContains(resp, "barbearia &amp; estilo")
        self.assertContains(resp, "favicon.png")

    def test_bigode_animado_na_barra_leva_para_inicio(self):
        self.assertTrue(self.client.login(username="cli@x.com", password="senha123"))
        resp = self.client.get(reverse("noticias"))
        self.assertContains(resp, 'class="bigode-nav svg-animado"')
        self.assertContains(resp, "<animateTransform")
        self.assertContains(resp, 'aria-label="BarberHouse, ir para o início"')
        self.assertNotContains(resp, "bigode.png")
        # O logo completo fica so na home
        self.assertNotContains(resp, "logo-completo")

    def test_logo_completo_svg_na_home_com_inter(self):
        self.assertTrue(self.client.login(username="cli@x.com", password="senha123"))
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, 'class="logo-completo svg-animado"')
        self.assertContains(resp, 'aria-label="BarberHouse - barbearia e estilo"')
        self.assertContains(resp, "family=Inter:wght@400;800")
        # comentarios de template de varias linhas nao podem vazar para o HTML
        self.assertNotContains(resp, "viewBox recortado")

    def test_arquivos_do_logo_existem(self):
        estaticos = BASE / "static" / "agendamentos"
        for nome in ("logo-bigode.png", "favicon.png", "apple-touch-icon.png"):
            self.assertTrue((estaticos / nome).exists(), nome)


class AberturaMarcaTests(BaseComPerfis):
    def test_abertura_aparece_so_na_primeira_home_apos_login(self):
        resp = self.client.post(reverse("login"), {"email": "cli@x.com", "senha": "senha123"}, follow=True)
        self.assertContains(resp, 'class="abertura-marca"')
        self.assertContains(resp, "com-abertura")
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, 'class="abertura-marca"')
        self.assertNotContains(resp, "com-abertura")

    def test_fundo_por_tela(self):
        self.assertTrue(self.client.login(username="cli@x.com", password="senha123"))
        self.assertContains(self.client.get(reverse("home")), "fundo-home")
        self.assertContains(self.client.get(reverse("agenda_cliente")), "fundo-agendamentos")
        self.assertContains(self.client.get(reverse("meus_agendamentos")), "fundo-agendamentos")
        noticias = self.client.get(reverse("noticias"))
        self.assertNotContains(noticias, "fundo-home")
        self.assertNotContains(noticias, "fundo-agendamentos")
