from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError, transaction
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from .forms import CadastroForm, AgendamentoForm
from .models import Cliente, Profissional, Servico, Agendamento
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, time, timedelta
from django.utils import timezone


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
                    usuario = User.objects.create_user(
                        username=dados["email"],
                        email=dados["email"],
                        password=dados["senha"]
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
                messages.success(request, "Conta criada com sucesso! Faca login para continuar.")
                return redirect("login")
        else:
            messages.error(request, "Por favor, corrija os erros no formulario.")
    else:
        form = CadastroForm()
    return render(request, "cadastro.html", {"form": form})
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        usuario = authenticate(request, username=email, password=senha)
        if usuario is not None:
            login(request, usuario)
            # A home mostra a abertura da marca uma unica vez, logo apos o login
            request.session['abertura_marca'] = True
            messages.success(request, 'Login realizado com sucesso!')
            return redirect('home')
        else:
            messages.error(request, 'Senha incorreta')
    return render(request, 'login.html')


@login_required
def home(request):
    # Determine user type
    if hasattr(request.user, 'profissional'):
        tipo = 'profissional'
    else:
        tipo = 'cliente'
    abertura_marca = request.session.pop('abertura_marca', False)
    return render(request, "home.html", {'tipo': tipo, 'abertura_marca': abertura_marca})


@login_required
def agenda_cliente(request):
    if not hasattr(request.user, "cliente"):
        messages.error(request, "Acesso negado. Esta área é apenas para clientes.")
        return redirect("home")

    cliente = request.user.cliente
    servicos = Servico.objects.all()
    profissionais = Profissional.objects.filter(agenda_aberta=True)
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
        ).select_related('servico', 'profissional').order_by('data_hora')
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
    ).select_related('servico', 'cliente').order_by('data_hora')
    context = {
        'profissional': profissional,
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
            resgatado = Cliente.objects.filter(
                pk=agendamento.cliente_id,
                cpf__isnull=False,
                cupom_resgatado_em__isnull=True,
            ).update(cupom_resgatado_em=timezone.now())
            if not resgatado:
                return JsonResponse({'error': 'Cupom j\u00e1 resgatado'}, status=409)
            agendamento.cupom_aplicado = True
        agendamento.save()

    return JsonResponse({
        'success': True,
        'status': agendamento.get_status_display(),
        'cancelado_por': agendamento.get_cancelado_por_display(),
    })


def noticias(request):
    cliente = None
    if request.user.is_authenticated:
        cliente = Cliente.objects.filter(usuario=request.user).first()
    return render(request, 'noticias.html', {'cliente': cliente})


def mais(request):
    """Placeholder view for more options page"""
    return render(request, 'mais.html')

class LogoutLimpandoMensagens(LogoutView):
    """Descarta mensagens pendentes para que n\u00e3o apare\u00e7am na tela de login."""

    def post(self, request, *args, **kwargs):
        list(messages.get_messages(request))
        return super().post(request, *args, **kwargs)
