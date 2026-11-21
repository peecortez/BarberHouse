import json
import re
import time as time_module
from io import StringIO
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .lembretes import enviar_lembretes_pendentes
from .models import Agendamento, Avaliacao, Cliente, EmailEnviado, Profissional, Servico

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


def link_do_email(mensagem, caminho):
    """Primeiro link do e-mail (versao texto) que comeca com o caminho dado."""
    achado = re.search(r"http://testserver(%s\S*)" % re.escape(caminho), mensagem.body)
    assert achado, mensagem.body
    return achado.group(1)


class ConfirmacaoCadastroTests(TestCase):
    dados = {
        "tipo": "cliente", "nome": "Ana Souza", "email": "ana@x.com",
        "telefone": "11999999999", "cpf": "529.982.247-25",
        "senha": "Senha123!", "senha_confirmacao": "Senha123!",
    }

    def cadastrar(self):
        return self.client.post(reverse("cadastro"), self.dados, follow=True)

    def test_cadastro_cria_conta_inativa_e_envia_link(self):
        resp = self.cadastrar()
        self.assertContains(resp, "Enviamos um link de confirmação para ana@x.com")
        self.assertFalse(User.objects.get(username="ana@x.com").is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@x.com"])
        self.assertIn("Ana", mail.outbox[0].body)
        self.assertTrue(mail.outbox[0].alternatives)  # tem versao HTML

    def test_link_ativa_a_conta_e_libera_o_login(self):
        self.cadastrar()
        link = link_do_email(mail.outbox[0], "/confirmar-email/")
        resp = self.client.get(link, follow=True)
        self.assertContains(resp, "E-mail confirmado")
        self.assertTrue(User.objects.get(username="ana@x.com").is_active)
        resp = self.client.post(reverse("login"), {"email": "ana@x.com", "senha": "Senha123!"})
        self.assertRedirects(resp, reverse("home"))

    def test_login_antes_de_confirmar_avisa_e_oferece_reenvio(self):
        self.cadastrar()
        resp = self.client.post(reverse("login"), {"email": "ana@x.com", "senha": "Senha123!"})
        self.assertContains(resp, "Confirme seu e-mail antes de entrar")
        self.assertContains(resp, f'action="{reverse("reenviar_confirmacao")}"')
        # Senha errada nao revela que a conta existe
        resp = self.client.post(reverse("login"), {"email": "ana@x.com", "senha": "errada"})
        self.assertNotContains(resp, "Confirme seu e-mail")

    def test_link_invalido_nao_ativa(self):
        self.cadastrar()
        resp = self.client.get(reverse("confirmar_email", args=["token-falso"]), follow=True)
        self.assertContains(resp, "Link inválido ou expirado")
        self.assertFalse(User.objects.get(username="ana@x.com").is_active)

    def test_link_expira_em_24h(self):
        self.cadastrar()
        link = link_do_email(mail.outbox[0], "/confirmar-email/")
        with mock.patch("django.core.signing.time.time", return_value=time_module.time() + 25 * 3600):
            self.client.get(link)
        self.assertFalse(User.objects.get(username="ana@x.com").is_active)

    def test_reenvio_respeita_intervalo_de_1_minuto(self):
        self.cadastrar()
        self.client.post(reverse("reenviar_confirmacao"), {"email": "ana@x.com"})
        self.assertEqual(len(mail.outbox), 1)  # o do cadastro acabou de sair
        EmailEnviado.objects.update(enviado_em=timezone.now() - timedelta(minutes=2))
        self.client.post(reverse("reenviar_confirmacao"), {"email": "ana@x.com"})
        self.assertEqual(len(mail.outbox), 2)

    def test_reenvio_para_email_desconhecido_responde_igual_e_nao_envia(self):
        resp = self.client.post(reverse("reenviar_confirmacao"), {"email": "ninguem@x.com"}, follow=True)
        self.assertContains(resp, "Se houver um cadastro pendente")
        self.assertEqual(len(mail.outbox), 0)

    def test_conta_desativada_pelo_admin_nao_reativa_pelo_link(self):
        self.cadastrar()
        link = link_do_email(mail.outbox[0], "/confirmar-email/")
        User.objects.filter(username="ana@x.com").update(last_login=timezone.now())
        self.client.get(link)
        self.assertFalse(User.objects.get(username="ana@x.com").is_active)


class RecuperarSenhaTests(TestCase):
    def setUp(self):
        u = User.objects.create_user("rui@x.com", "rui@x.com", "SenhaAntiga1!")
        Cliente.objects.create(usuario=u, nome="Rui Lima", email="rui@x.com", telefone="1")

    def test_login_tem_link_esqueci_a_senha(self):
        self.assertContains(self.client.get(reverse("login")), f'href="{reverse("password_reset")}"')

    def test_fluxo_completo_de_redefinicao(self):
        resp = self.client.post(reverse("password_reset"), {"email": "rui@x.com"})
        self.assertRedirects(resp, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Redefina sua senha na BarberHouse")
        self.assertIn("Rui", mail.outbox[0].body)

        link = link_do_email(mail.outbox[0], "/redefinir-senha/")
        resp = self.client.get(link, follow=True)
        self.assertContains(resp, "Crie uma")
        resp = self.client.post(resp.redirect_chain[-1][0], {
            "new_password1": "NovaSenha456!", "new_password2": "NovaSenha456!",
        })
        self.assertRedirects(resp, reverse("password_reset_complete"))
        self.assertTrue(self.client.login(username="rui@x.com", password="NovaSenha456!"))

        # O link so vale uma vez
        self.client.logout()
        self.assertContains(self.client.get(link, follow=True), "Link <span class=\"destaque\">expirado</span>", html=False)

    def test_tela_de_nova_senha_confere_a_confirmacao_sem_texto_sobrando(self):
        self.client.post(reverse("password_reset"), {"email": "rui@x.com"})
        resp = self.client.get(link_do_email(mail.outbox[0], "/redefinir-senha/"), follow=True)
        self.assertContains(resp, 'id="formRedefinirSenha"')
        self.assertContains(resp, 'id="senhaFeedback"')
        self.assertNotContains(resp, "gerenciador de senhas")
        self.assertNotContains(resp, 'autocomplete="username"')

    def test_nenhum_template_tem_comentario_de_varias_linhas_com_chaves(self):
        # {# #} do Django so vale numa linha: em varias, o texto aparece na tela
        for arquivo in TEMPLATES.rglob("*.html"):
            for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
                if "{#" in linha:
                    self.assertIn("#}", linha.split("{#", 1)[1], f"{arquivo.name}:{numero}")

    def test_login_aceita_email_com_maiusculas(self):
        resp = self.client.post(reverse("login"), {"email": "  Rui@X.com ", "senha": "SenhaAntiga1!"})
        self.assertRedirects(resp, reverse("home"))

    def test_login_errado_mantem_o_email_digitado(self):
        resp = self.client.post(reverse("login"), {"email": "rui@x.com", "senha": "errada"})
        self.assertContains(resp, "E-mail ou senha incorretos.")
        self.assertContains(resp, 'value="rui@x.com"')

    def test_email_desconhecido_responde_igual_e_nao_envia(self):
        resp = self.client.post(reverse("password_reset"), {"email": "ninguem@x.com"})
        self.assertRedirects(resp, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_pedidos_seguidos_enviam_um_so(self):
        for _ in range(3):
            self.client.post(reverse("password_reset"), {"email": "rui@x.com"})
        self.assertEqual(len(mail.outbox), 1)

    def test_admin_com_o_mesmo_email_nao_rouba_o_link(self):
        # Um admin mais antigo (username "joao") com o mesmo e-mail do cliente:
        # o link tem de redefinir a conta que o login usa (username = e-mail).
        Cliente.objects.all().delete()
        User.objects.all().delete()
        User.objects.create_superuser("joao", "rui@x.com", "SenhaDoAdmin1!")
        u = User.objects.create_user("rui@x.com", "rui@x.com", "SenhaAntiga1!")
        Cliente.objects.create(usuario=u, nome="Rui Lima", email="rui@x.com", telefone="1")

        self.client.post(reverse("password_reset"), {"email": "rui@x.com"})
        self.assertEqual(len(mail.outbox), 1)
        resp = self.client.get(link_do_email(mail.outbox[0], "/redefinir-senha/"), follow=True)
        self.client.post(resp.redirect_chain[-1][0], {
            "new_password1": "NovaSenha456!", "new_password2": "NovaSenha456!",
        })
        resp = self.client.post(reverse("login"), {"email": "rui@x.com", "senha": "NovaSenha456!"})
        self.assertRedirects(resp, reverse("home"))
        self.assertTrue(User.objects.get(username="joao").check_password("SenhaDoAdmin1!"))


class EmailsAgendamentoTests(BaseComPerfis):
    def test_agendar_envia_horario_reservado(self):
        self.logar("cli@x.com")
        corpo = {"servico_id": self.servico.id, "profissional_id": self.prof.id, "data_hora": f"{self.amanha}T15:00"}
        self.client.post(reverse("agendar_servico"), json.dumps(corpo), content_type="application/json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["cli@x.com"])
        self.assertEqual(mail.outbox[0].subject, "Seu horário está reservado")
        self.assertIn("15:00", mail.outbox[0].body)
        self.assertIn("Barbeiro", mail.outbox[0].body)

    def test_confirmar_envia_confirmacao(self):
        self.logar("bar@x.com")
        self.acao("confirmar")
        self.assertEqual(mail.outbox[-1].subject, "Seu horário foi confirmado")

    def test_cancelamento_pelo_profissional_avisa_o_cliente(self):
        self.logar("bar@x.com")
        self.acao("cancelar")
        self.assertEqual(mail.outbox[-1].subject, "Seu agendamento foi cancelado")
        self.assertIn("precisou cancelar", mail.outbox[-1].body)

    def test_cancelamento_pelo_cliente_confirma_o_cancelamento(self):
        self.logar("cli@x.com")
        self.acao("cancelar")
        self.assertIn("Seu cancelamento foi registrado", mail.outbox[-1].body)

    def test_concluir_convida_a_avaliar(self):
        self.logar("bar@x.com")
        self.acao("concluir")
        self.assertEqual(mail.outbox[-1].subject, "Como foi seu atendimento?")
        self.assertIn(reverse("avaliar_atendimento", args=[self.agendamento.id]), mail.outbox[-1].body)

    @override_settings(EMAIL_LIMITE_DIARIO=1)
    def test_teto_diario_para_de_enviar(self):
        self.logar("bar@x.com")
        self.acao("confirmar")
        with self.assertLogs("agendamentos.emails", level="WARNING"):
            self.acao("concluir")
        self.assertEqual(len(mail.outbox), 1)
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, "CONCLUIDO")  # a acao segue normal

    def test_falha_no_envio_nao_derruba_a_acao(self):
        self.logar("bar@x.com")
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("smtp fora")), \
                self.assertLogs("agendamentos.emails", level="ERROR"):
            resp = self.acao("confirmar")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(EmailEnviado.objects.get().sucesso)


class LembretesTests(BaseComPerfis):
    def marcar(self, daqui_horas, criado_ha_horas=48, **extra):
        agora = timezone.now()
        ag = Agendamento.objects.create(
            cliente=self.cliente, profissional=self.prof, servico=self.servico,
            data_hora=agora + timedelta(hours=daqui_horas), **extra,
        )
        Agendamento.objects.filter(pk=ag.pk).update(criado_em=agora - timedelta(hours=criado_ha_horas))
        return ag

    def setUp(self):
        super().setUp()
        self.agendamento.delete()

    def test_envia_um_lembrete_so(self):
        ag = self.marcar(20)
        self.assertEqual(enviar_lembretes_pendentes(), 1)
        self.assertEqual(enviar_lembretes_pendentes(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.startswith("Lembrete: seu horário é"))
        ag.refresh_from_db()
        self.assertIsNotNone(ag.lembrete_enviado_em)

    def test_nao_lembra_quem_nao_deve(self):
        self.marcar(72)                                          # ainda falta muito
        self.marcar(20, status=Agendamento.Status.CANCELADO)     # cancelado
        self.marcar(20, criado_ha_horas=2)                       # marcou em cima da hora
        self.marcar(-1)                                          # ja passou
        self.assertEqual(enviar_lembretes_pendentes(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_cliente_com_email_nao_confirmado_nao_recebe(self):
        self.marcar(20)
        User.objects.filter(username="cli@x.com").update(is_active=False)
        self.assertEqual(enviar_lembretes_pendentes(), 0)

    def test_falha_no_envio_tenta_de_novo_depois(self):
        ag = self.marcar(20)
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("smtp fora")), \
                self.assertLogs("agendamentos.emails", level="ERROR"):
            self.assertEqual(enviar_lembretes_pendentes(), 0)
        ag.refresh_from_db()
        self.assertIsNone(ag.lembrete_enviado_em)
        self.assertEqual(enviar_lembretes_pendentes(), 1)

    def test_comando_manual(self):
        self.marcar(20)
        call_command("enviar_lembretes", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)


class AvaliacaoTests(BaseComPerfis):
    def setUp(self):
        super().setUp()
        Agendamento.objects.filter(pk=self.agendamento.pk).update(status=Agendamento.Status.CONCLUIDO)
        self.url = reverse("avaliar_atendimento", args=[self.agendamento.id])

    def test_cliente_avalia_atendimento_concluido(self):
        self.logar("cli@x.com")
        self.assertContains(self.client.get(reverse("meus_agendamentos")), f'href="{self.url}"')
        resp = self.client.post(self.url, {"nota": "4", "comentario": "Corte top"}, follow=True)
        self.assertContains(resp, "Obrigado pela avaliação")
        self.assertContains(resp, 'aria-label="4 de 5 estrelas"')
        avaliacao = Avaliacao.objects.get()
        self.assertEqual((avaliacao.nota, avaliacao.comentario), (4, "Corte top"))

    def test_avalia_uma_vez_so(self):
        self.logar("cli@x.com")
        self.client.post(self.url, {"nota": "5"})
        self.client.post(self.url, {"nota": "1"})
        self.assertEqual(Avaliacao.objects.get().nota, 5)

    def test_nota_fora_de_1_a_5_e_recusada(self):
        self.logar("cli@x.com")
        for nota in ("0", "6", ""):
            resp = self.client.post(self.url, {"nota": nota})
            self.assertEqual(resp.status_code, 200)
            self.assertIn("nota", resp.context["form"].errors)
        self.assertFalse(Avaliacao.objects.exists())

    def test_nao_avalia_atendimento_nao_concluido(self):
        Agendamento.objects.filter(pk=self.agendamento.pk).update(status=Agendamento.Status.AGENDADO)
        self.logar("cli@x.com")
        self.client.post(self.url, {"nota": "5"})
        self.assertFalse(Avaliacao.objects.exists())

    def test_nao_avalia_agendamento_de_outro_cliente(self):
        u = User.objects.create_user("outro@x.com", "outro@x.com", "senha123")
        Cliente.objects.create(usuario=u, nome="Outro", email="outro@x.com", telefone="9")
        self.logar("outro@x.com")
        self.assertEqual(self.client.post(self.url, {"nota": "1"}).status_code, 404)
        self.logar("bar@x.com")
        self.client.post(self.url, {"nota": "1"})
        self.assertFalse(Avaliacao.objects.exists())

    def test_media_aparece_para_profissional_e_na_escolha_do_cliente(self):
        Avaliacao.objects.create(agendamento=self.agendamento, nota=4, comentario="Muito bom")
        self.logar("bar@x.com")
        resp = self.client.get(reverse("gerenciar_agenda"))
        self.assertContains(resp, "4,0")
        self.assertContains(resp, "1 avaliação")
        self.assertContains(resp, "Muito bom")
        self.logar("cli@x.com")
        self.assertContains(self.client.get(reverse("agenda_cliente")), "Barbeiro · ★ 4,0 (1)")

    def test_link_do_email_pede_login_e_volta_para_a_avaliacao(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, f'{reverse("login")}?next={self.url}')
        resp = self.client.post(f'{reverse("login")}?next={self.url}', {"email": "cli@x.com", "senha": "senha123"})
        self.assertRedirects(resp, self.url)

    def test_login_ignora_next_para_outro_site(self):
        resp = self.client.post(f'{reverse("login")}?next=https://malicioso.com/', {"email": "cli@x.com", "senha": "senha123"})
        self.assertRedirects(resp, reverse("home"))
