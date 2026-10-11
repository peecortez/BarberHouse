from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from .forms import CadastroForm, AgendamentoForm
from .models import Cliente, Profissional, Servico, Agendamento
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta
from django.utils import timezone


def cadastro(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data

            usuario = User.objects.create_user(
                username=dados['email'],
                email=dados['email'],
                password=dados['senha']
            )

            if dados['tipo'] == 'cliente':
                Cliente.objects.create(
                    usuario=usuario,
                    nome=dados['nome'],
                    email=dados['email'],
                    telefone=dados['telefone']
                )
            else:
                Profissional.objects.create(
                    usuario=usuario,
                    nome=dados['nome'],
                    email=dados['email'],
                    telefone=dados['telefone']
                )

            messages.success(request, 'Conta criada com sucesso! Faça login para continuar.')
            return redirect('login')
    else:
        form = CadastroForm()

    return render(request, 'cadastro.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        usuario = authenticate(request, username=email, password=senha)
        if usuario is not None:
            login(request, usuario)
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
    return render(request, "home.html", {'tipo': tipo})


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
    """API endpoint to get available time slots for a service and professional"""
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
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
    except (Servico.DoesNotExist, Profissional.DoesNotExist, ValueError):
        return JsonResponse({"error": "Invalid parameters"}, status=400)

    # Get existing appointments for this professional on this date with their services
    existentes = Agendamento.objects.filter(
        profissional=profissional,
        data_hora__date=data
    ).exclude(status=Agendamento.Status.CANCELADO).select_related('servico')

    # Generate time slots from 8:00 to 18:00
    horarios = []
    hora_inicio = timezone.make_aware(datetime.combine(data, datetime.min.time().replace(hour=8)))
    hora_fim = timezone.make_aware(datetime.combine(data, datetime.min.time().replace(hour=18)))

    atual = hora_inicio
    while atual < hora_fim:
        # Check if this time slot is available
        conflito = False
        for existente in existentes:
            # Calculate end time of existing appointment
            existente_fim = existente.data_hora + timedelta(minutes=existente.servico.duracao_minutos)
            # Calculate end time of proposed slot
            proposta_fim = atual + timedelta(minutes=servico.duracao_minutos)

            # Check for overlap: [atual, proposta_fim) overlaps with [existente.data_hora, existente_fim)
            if atual < existente_fim and existente.data_hora < proposta_fim:
                conflito = True
                break

        if not conflito:
            horarios.append(atual.strftime('%H:%M'))

        atual += timedelta(minutes=30)  # 30-minute intervals

    return JsonResponse({"horarios": horarios})


@login_required
def agendar_servico(request):
    """View to create a new appointment"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if not hasattr(request.user, 'cliente'):
        return JsonResponse({'error': 'Access denied'}, status=403)

    try:
        data = json.loads(request.body)
        servico_id = data.get('servico_id')
        profissional_id = data.get('profissional_id')
        data_hora_str = data.get('data_hora')

        if not all([servico_id, profissional_id, data_hora_str]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        servico = Servico.objects.get(id=servico_id)
        profissional = Profissional.objects.get(id=profissional_id)
        data_hora = timezone.make_aware(datetime.strptime(data_hora_str, '%Y-%m-%dT%H:%M'))

        # Check if the time slot is still available
        conflito = Agendamento.objects.filter(
            profissional=profissional,
            data_hora=data_hora
        ).exclude(status=Agendamento.Status.CANCELADO).exists()

        if conflito:
            return JsonResponse({'error': 'Time slot no longer available'}, status=409)

        # Create the appointment
        agendamento = Agendamento.objects.create(
            cliente=request.user.cliente,
            profissional=profissional,
            servico=servico,
            data_hora=data_hora
        )

        return JsonResponse({
            'success': True,
            'message': 'Appointment scheduled successfully!',
            'agendamento_id': agendamento.id
        })

    except (Servico.DoesNotExist, Profissional.DoesNotExist, ValueError) as e:
        return JsonResponse({'error': 'Invalid data'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


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
        agendamentos = []
        tipo = None

    context = {
        'agendamentos': agendamentos,
        'tipo': tipo
    }
    return render(request, 'meus_agendamentos.html', context)


@login_required
def gerenciar_agenda(request):
    """View for professionals to manage their schedule"""
    if not hasattr(request.user, 'profissional'):
        messages.error(request, 'Access denied. This area is for professionals only.')
        return redirect('home')

    profissional = request.user.profissional
    agendamentos = Agendamento.objects.filter(
        profissional=profissional
    ).select_related('servico', 'cliente').order_by('data_hora')
    context = {
        'profissional': profissional,
        'agendamentos': agendamentos
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
    except json.JSONDecodeError:
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

    agendamento.status = new_status
    agendamento.save()

    return JsonResponse({
        'success': True,
        'status': agendamento.get_status_display()
    })


def noticias(request):
    """Placeholder view for news page"""
    return render(request, 'noticias.html')


def mais(request):
    """Placeholder view for more options page"""
    return render(request, 'mais.html')