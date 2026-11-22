from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError, transaction
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from .emails import (
    bloqueado_para_destinatario,
    enviar_aviso_agendamento,
    enviar_confirmacao_cadastro,
    ler_token_confirmacao,
)
from .forms import AvaliacaoForm, CadastroForm, AgendamentoForm
from .models import Avaliacao, Cliente, Profissional, Servico, Agendamento
from django.contrib import messages
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
import json
from datetime import datetime, time, timedelta
from django.utils import timezone


def _nome_do_perfil(usuario):
    perfil = getattr(usuario, 'cliente', None) or getattr(usuario, 'profissional', None)
    return perfil.nome if perfil else ''


def _com_media_de_avaliacoes(profissionais):
    return profissionais.annotate(
        media_avaliacoes=Avg('agendamento__avaliacao__nota'),
        total_avaliacoes=Count('agendamento__avaliacao'),
    )


def _tem_conflito(profissional, servico, inicio):
    fim = inicio + timedelta(minutes=servico.duracao_minutos)
    existentes = Agendamento.objects.filter(
        profissional=profissional,
        data_hora__date=inicio.date()
    ).exclude(status=Agendamento.Status.CANCELADO).select_related('servico')
    return any(
        inicio < existente.data_hora + timedelta(minutes=existente.servico.duracao_minutos)
        and existente.data_hora < fim
        for existente in existentes
    )


def cadastro(request):
    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with transaction.atomic():
                    # A conta so e ativada quando a pessoa clica no link do e-mail
                    usuario = User.objects.create_user(
                        username=dados["email"],
                        email=dados["email"],
                        password=dados["senha"],
                        is_active=False,
                    )
                    perfil = Cliente if dados["tipo"] == "cliente" else Profissional
                    perfil.objects.create(
                        usuario=usuario,
                        nome=dados["nome"],
                        email=dados["email"],
                        telefone=dados["telefone"],
                        cpf=dados["cpf"],
                    )
            except IntegrityError:
                form.add_error(None, "E-mail ou CPF já cadastrado. Entre ou use outros dados.")
            else:
                if enviar_confirmacao_cadastro(request, usuario, dados["nome"]):
                    messages.success(
                        request,
                        f"Conta criada! Enviamos um link de confirmação para {usuario.email}. "
                        "Abra o e-mail para ativar sua conta (confira também o spam).",
                    )
                else:
                    messages.warning(
                        request,
                        "Conta criada, mas não conseguimos enviar o e-mail de confirmação agora. "
                        "Entre com seu e-mail e senha para tentar de novo.",
                    )
                return redirect("login")
        else:
            messages.error(request, "Por favor, corrija os erros no formulario.")
    else:
        form = CadastroForm()
    return render(request, "cadastro.html", {"form": form})
def login_view(request):
    # "next": quem veio de um link (ex.: "Avaliar atendimento" no e-mail) volta para la
    destino = request.POST.get('next') or request.GET.get('next') or ''
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        destino = ''
    contexto = {'next': destino}

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        senha = request.POST.get('senha') or ''
        contexto['email_digitado'] = email
        # E-mail sem diferenca de maiusculas (o celular as vezes poe a primeira letra maiuscula)
        conta = User.objects.filter(username__iexact=email).only('username').first()
        usuario = authenticate(request, username=conta.username if conta else email, password=senha)
        if usuario is not None:
            login(request, usuario)
            messages.success(request, 'Login realizado com sucesso!')
            if destino:
                return redirect(destino)
            # A home mostra a abertura da marca uma unica vez, logo apos o login
            request.session['abertura_marca'] = True
            return redirect('home')

        # Senha certa, mas o e-mail ainda nao foi confirmado: oferece reenviar o link
        pendente = User.objects.filter(
            username__iexact=email, is_active=False, last_login__isnull=True,
        ).first()
        if pendente is not None and pendente.check_password(senha):
            messages.warning(request, 'Confirme seu e-mail antes de entrar. Procure o link na sua caixa de entrada (e no spam).')
            contexto['email_pendente'] = pendente.email
        else:
            messages.error(request, 'E-mail ou senha incorretos.')
    return render(request, 'login.html', contexto)


def confirmar_email(request, token):
    """Link do e-mail de cadastro: ativa a conta."""
    usuario_id = ler_token_confirmacao(token)
    usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None
    # last_login preenchido = conta ja usada e desativada pelo admin: o link nao reativa
    if usuario is None or (not usuario.is_active and usuario.last_login is not None):
        messages.error(request, 'Link inválido ou expirado. Entre com seu e-mail e senha para receber um novo.')
    elif usuario.is_active:
        messages.success(request, 'Seu e-mail já estava confirmado. É só entrar.')
    else:
        usuario.is_active = True
        usuario.save(update_fields=['is_active'])
        messages.success(request, 'E-mail confirmado! Agora é só entrar.')
    return redirect('login')


@require_POST
def reenviar_confirmacao(request):
    email = (request.POST.get('email') or '').strip()
    usuario = User.objects.filter(
        username__iexact=email, is_active=False, last_login__isnull=True,
    ).first()
    if usuario is not None and not bloqueado_para_destinatario(usuario.email, 'confirmacao'):
        enviar_confirmacao_cadastro(request, usuario, _nome_do_perfil(usuario))
    # Mesma resposta em todos os casos: a tela nao revela quais e-mails tem cadastro
    messages.success(request, 'Se houver um cadastro pendente para esse e-mail, enviamos um novo link. Se não chegar, aguarde um minuto e tente de novo.')
    return redirect('login')


@login_required
def home(request):
    # Determine user type
    if hasattr(request.user, 'profissional'):
        tipo = 'profissional'
    else:
        tipo = 'cliente'
    abertura_marca = request.session.pop('abertura_marca', False)
    contexto = {'tipo': tipo, 'abertura_marca': abertura_marca}
    if tipo == 'cliente':
        contexto['avaliacoes_destaque'] = _avaliacoes_em_destaque()
    return render(request, "home.html", contexto)


def _avaliacoes_em_destaque(limite=8):
    """Avaliacoes mais recentes com comentario, para os cards da home do cliente."""
    return (
        Avaliacao.objects.exclude(comentario='')
        .select_related('agendamento__cliente', 'agendamento__profissional', 'agendamento__servico')
        .order_by('-criado_em')[:limite]
    )


@login_required
def agenda_cliente(request):
    if not hasattr(request.user, "cliente"):
        messages.error(request, "Acesso negado. Esta área é apenas para clientes.")
        return redirect("home")

    cliente = request.user.cliente
    servicos = Servico.objects.all()
    profissionais = _com_media_de_avaliacoes(Profissional.objects.filter(agenda_aberta=True))
    from datetime import date
    context = {
        "cliente": cliente,
        "servicos": servicos,
        "profissionais": profissionais,
        "today": date.today()
    }
    return render(request, "agenda_cliente.html", context)


@login_required
def horarios_disponiveis(request):
    """Retorna hor?rios livres dentro do expediente do profissional."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    servico_id = request.GET.get("servico")
    profissional_id = request.GET.get("profissional")
    data_str = request.GET.get("data")
    if not all([servico_id, profissional_id, data_str]):
        return JsonResponse({"error": "Missing required parameters"}, status=400)
    try:
        servico = Servico.objects.get(id=servico_id)
        profissional = Profissional.objects.get(id=profissional_id)
        data = datetime.strptime(data_str, "%Y-%m-%d").date()
    except (Servico.DoesNotExist, Profissional.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Invalid parameters"}, status=400)
    if not profissional.agenda_aberta or servico.duracao_minutos <= 0 or data < timezone.localdate():
        return JsonResponse({"horarios": []})
    abertura = timezone.make_aware(datetime.combine(data, time(8, 0)))
    fechamento = timezone.make_aware(datetime.combine(data, time(18, 0)))
    atual = abertura
    agora = timezone.now()
    horarios = []
    while atual < fechamento:
        fim = atual + timedelta(minutes=servico.duracao_minutos)
        if atual > agora and fim <= fechamento and not _tem_conflito(profissional, servico, atual):
            horarios.append(atual.strftime("%H:%M"))
        atual += timedelta(minutes=30)
    return JsonResponse({"horarios": horarios})

@login_required
def agendar_servico(request):
    """Cria um agendamento ap?s validar perfil, expediente e conflitos."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not hasattr(request.user, "cliente"):
        return JsonResponse({"error": "Access denied"}, status=403)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            return JsonResponse({"error": "Invalid data"}, status=400)
        is_json = True
        servico_id = payload.get("servico_id")
        profissional_id = payload.get("profissional_id")
        data_hora_str = payload.get("data_hora")
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        is_json = False
        servico_id = request.POST.get("servico")
        profissional_id = request.POST.get("profissional")
        data_str = request.POST.get("data")
        horario_str = request.POST.get("horario")
        if not all([servico_id, profissional_id, data_str, horario_str]):
            messages.error(request, "Campos obrigat\u00f3rios faltando.")
            return redirect("agenda_cliente")
        data_hora_str = f"{data_str}T{horario_str}"
    if not all([servico_id, profissional_id, data_hora_str]):
        if is_json:
            return JsonResponse({"error": "Missing required fields"}, status=400)
        messages.error(request, "Campos obrigat\u00f3rios faltando.")
        return redirect("agenda_cliente")
    try:
        servico = Servico.objects.get(id=servico_id)
        profissional = Profissional.objects.get(id=profissional_id)
        data_hora = timezone.make_aware(datetime.strptime(data_hora_str, "%Y-%m-%dT%H:%M"))
    except (Servico.DoesNotExist, Profissional.DoesNotExist, ValueError, TypeError):
        if is_json:
            return JsonResponse({"error": "Invalid data"}, status=400)
        messages.error(request, "Dados inv\u00e1lidos.")
        return redirect("agenda_cliente")
    abertura = timezone.make_aware(datetime.combine(data_hora.date(), time(8, 0)))
    fechamento = timezone.make_aware(datetime.combine(data_hora.date(), time(18, 0)))
    if (
        not profissional.agenda_aberta
        or servico.duracao_minutos <= 0
        or data_hora.date() < timezone.localdate()
        or data_hora <= timezone.now()
        or data_hora.minute % 30 != 0
        or data_hora < abertura
        or data_hora + timedelta(minutes=servico.duracao_minutos) > fechamento
    ):
        if is_json:
            return JsonResponse({"error": "Invalid or unavailable time"}, status=400)
        messages.error(request, "Hor\u00e1rio inv\u00e1lido ou agenda fechada.")
        return redirect("agenda_cliente")
    if _tem_conflito(profissional, servico, data_hora):
        if is_json:
            return JsonResponse({"error": "Time slot no longer available"}, status=409)
        messages.error(request, "Hor\u00e1rio n\u00e3o dispon\u00edvel.")
        return redirect("agenda_cliente")
    agendamento = Agendamento.objects.create(
        cliente=request.user.cliente,
        profissional=profissional,
        servico=servico,
        data_hora=data_hora
    )
    enviar_aviso_agendamento(request, agendamento, 'criado')
    if is_json:
        return JsonResponse({
            "success": True,
            "message": "Agendamento realizado com sucesso!",
            "agendamento_id": agendamento.id
        })
    messages.success(request, "Agendamento realizado com sucesso")
    return redirect("meus_agendamentos")

@login_required
def meus_agendamentos(request):
    """View for users to see their appointments"""
    if hasattr(request.user, 'profissional'):
        return redirect('gerenciar_agenda')

    if hasattr(request.user, 'cliente'):
        agendamentos = Agendamento.objects.filter(
            cliente=request.user.cliente
        ).select_related('servico', 'profissional', 'avaliacao').order_by('data_hora')
        tipo = 'cliente'
    else:
        agendamentos = Agendamento.objects.none()
        tipo = None

    context = {
        'agendamentos': agendamentos,
        'agendamentos_ativos': agendamentos.filter(
            status__in=[Agendamento.Status.AGENDADO, Agendamento.Status.CONFIRMADO]
        ),
        'agendamentos_concluidos': agendamentos.filter(status=Agendamento.Status.CONCLUIDO),
        'agendamentos_cancelados': agendamentos.filter(status=Agendamento.Status.CANCELADO),
        'tipo': tipo
    }
    return render(request, 'meus_agendamentos.html', context)


@login_required
def gerenciar_agenda(request):
    """View for professionals to manage their schedule"""
    if not hasattr(request.user, 'profissional'):
        messages.error(request, "Acesso negado. Esta \u00e1rea \u00e9 apenas para profissionais.")
        return redirect('home')

    profissional = request.user.profissional
    agendamentos = Agendamento.objects.filter(
        profissional=profissional
    ).select_related('servico', 'cliente', 'avaliacao').order_by('data_hora')
    avaliacoes = Avaliacao.objects.filter(agendamento__profissional=profissional).aggregate(
        media=Avg('nota'), total=Count('id'),
    )
    context = {
        'profissional': profissional,
        'avaliacoes': avaliacoes,
        'agendamentos': agendamentos,
        'agendamentos_ativos': agendamentos.filter(
            status__in=[Agendamento.Status.AGENDADO, Agendamento.Status.CONFIRMADO]
        ),
        'agendamentos_concluidos': agendamentos.filter(status=Agendamento.Status.CONCLUIDO),
        'agendamentos_cancelados': agendamentos.filter(status=Agendamento.Status.CANCELADO),
    }
    return render(request, 'gerenciar_agenda.html', context)


@login_required
def toggle_agenda_aberta(request):
    """API endpoint for professionals to open/close their agenda"""
    if not hasattr(request.user, 'profissional'):
        return JsonResponse({'error': 'Access denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        profissional = request.user.profissional
        profissional.agenda_aberta = not profissional.agenda_aberta
        profissional.save()

        status = 'aberta' if profissional.agenda_aberta else 'fechada'
        return JsonResponse({
            'success': True,
            'message': f'Agenda now {status}',
            'agenda_aberta': profissional.agenda_aberta
        })
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def atualizar_status(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)
    try:
        data = json.loads(request.body)
        acao = data.get('acao')
        aplicar_cupom = data.get('cupom') is True
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if acao not in ['confirmar', 'concluir', 'cancelar']:
        return JsonResponse({'error': 'Invalid action'}, status=400)

    # Check permissions and transitions
    user = request.user
    is_profissional = hasattr(user, 'profissional')
    is_cliente = hasattr(user, 'cliente')

    if is_profissional:
        profissional = user.profissional
        if agendamento.profissional != profissional:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    elif is_cliente:
        cliente = user.cliente
        if agendamento.cliente != cliente:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    else:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    current_status = agendamento.status
    new_status = None

    if acao == 'confirmar':
        if current_status != Agendamento.Status.AGENDADO:
            return JsonResponse({'error': 'Invalid status transition'}, status=409)
        new_status = Agendamento.Status.CONFIRMADO
        # Only the dono profissional can confirm
        if not is_profissional or agendamento.profissional != user.profissional:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    elif acao == 'concluir':
        if current_status not in [Agendamento.Status.AGENDADO, Agendamento.Status.CONFIRMADO]:
            return JsonResponse({'error': 'Invalid status transition'}, status=409)
        new_status = Agendamento.Status.CONCLUIDO
        # Only the dono profissional can concluir
        if not is_profissional or agendamento.profissional != user.profissional:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    elif acao == 'cancelar':
        if current_status not in [Agendamento.Status.AGENDADO, Agendamento.Status.CONFIRMADO]:
            return JsonResponse({'error': 'Invalid status transition'}, status=409)
        new_status = Agendamento.Status.CANCELADO
        # Either the dono profissional or the dono cliente can cancel
        if not ( (is_profissional and agendamento.profissional == user.profissional) or
                 (is_cliente and agendamento.cliente == user.cliente) ):
            return JsonResponse({'error': 'Permission denied'}, status=403)

    if aplicar_cupom and acao != 'concluir':
        return JsonResponse({'error': 'Invalid action'}, status=400)

    agendamento.status = new_status
    if acao == 'cancelar':
        agendamento.cancelado_por = (
            Agendamento.CanceladoPor.PROFISSIONAL
            if is_profissional
            else Agendamento.CanceladoPor.CLIENTE
        )
    with transaction.atomic():
        if aplicar_cupom:
            # So aplica cupom que o cliente resgatou e ainda nao usou.
            usado = Cliente.objects.filter(
                pk=agendamento.cliente_id,
                cpf__isnull=False,
                cupom_resgatado_em__isnull=False,
                cupom_usado_em__isnull=True,
            ).update(cupom_usado_em=timezone.now())
            if not usado:
                cliente = Cliente.objects.get(pk=agendamento.cliente_id)
                erro = 'Cupom j\u00e1 usado' if cliente.cupom_usado else 'O cliente ainda n\u00e3o resgatou o cupom'
                return JsonResponse({'error': erro}, status=409)
            agendamento.cupom_aplicado = True
        agendamento.save()

    evento = {'confirmar': 'confirmado', 'cancelar': 'cancelado', 'concluir': 'concluido'}[acao]
    enviar_aviso_agendamento(request, agendamento, evento)

    return JsonResponse({
        'success': True,
        'status': agendamento.get_status_display(),
        'cancelado_por': agendamento.get_cancelado_por_display(),
    })


@login_required
def avaliar_atendimento(request, agendamento_id):
    """O cliente da de 1 a 5 estrelas (e um comentario opcional) a um atendimento concluido."""
    cliente = getattr(request.user, 'cliente', None)
    if cliente is None:
        messages.error(request, "Só clientes podem avaliar atendimentos.")
        return redirect('home')
    agendamento = get_object_or_404(
        Agendamento.objects.select_related('servico', 'profissional'),
        id=agendamento_id, cliente=cliente,
    )
    if agendamento.status != Agendamento.Status.CONCLUIDO:
        messages.error(request, "Só dá para avaliar atendimentos concluídos.")
        return redirect('meus_agendamentos')
    if hasattr(agendamento, 'avaliacao'):
        messages.info(request, "Você já avaliou este atendimento. Obrigado!")
        return redirect('meus_agendamentos')

    if request.method == 'POST':
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.agendamento = agendamento
            try:
                avaliacao.save()
            except IntegrityError:  # clique duplo: a primeira ja salvou
                pass
            messages.success(request, "Obrigado pela avaliação!")
            return redirect('meus_agendamentos')
    else:
        form = AvaliacaoForm()
    return render(request, 'avaliar.html', {'form': form, 'agendamento': agendamento})


def noticias(request):
    cliente = None
    if request.user.is_authenticated:
        cliente = Cliente.objects.filter(usuario=request.user).first()
    return render(request, 'noticias.html', {'cliente': cliente})


@login_required
@require_POST
def resgatar_cupom(request):
    """O cliente pega o cupom em Noticias. Sem isso, o profissional nao pode aplica-lo."""
    cliente = getattr(request.user, 'cliente', None)
    if cliente is None:
        return JsonResponse({'error': 'A promoção é exclusiva para contas de cliente.'}, status=403)
    if not cliente.cpf:
        return JsonResponse({'error': 'Sua conta ainda não tem CPF cadastrado.'}, status=400)

    # Idempotente: um segundo clique nao muda a data do primeiro.
    Cliente.objects.filter(pk=cliente.pk, cupom_resgatado_em__isnull=True).update(
        cupom_resgatado_em=timezone.now()
    )
    if request.headers.get('X-Requested-With') == 'fetch':
        return JsonResponse({'codigo': cliente.codigo_promocao})
    return redirect('noticias')


def sobre(request):
    """Historia, espaco (fotos) e contatos da barbearia. Conteudo fixo, aberto a todos."""
    return render(request, 'sobre.html')

class LogoutLimpandoMensagens(LogoutView):
    """Descarta mensagens pendentes para que n\u00e3o apare\u00e7am na tela de login."""

    def post(self, request, *args, **kwargs):
        list(messages.get_messages(request))
        return super().post(request, *args, **kwargs)
