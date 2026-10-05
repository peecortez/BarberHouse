from django.shortcuts import render, redirect
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
            return redirect('home')
    return render(request, 'login.html')


@login_required
def home(request):
    return render(request, 'home.html')


@login_required
def agenda_cliente(request):
    """View for clients to schedule appointments"""
    if not hasattr(request.user, 'cliente'):
        messages.error(request, 'Acesso negado. Esta área é apenas para clientes.')
        return redirect('home')

    cliente = request.user.cliente
    servicos = Servico.objects.all()
    profissionais = Profissional.objects.filter(agenda_aberta=True)

    context = {
        'cliente': cliente,
        'servicos': servicos,
        'profissionais': profissionais
    }
    return render(request, 'agenda_cliente.html', context)


@login_required
def horarios_disponiveis(request):
    """API endpoint to get available time slots for a service and professional"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    servico_id = request.GET.get('servico')
    profissional_id = request.GET.get('profissional')
    data_str = request.GET.get('data')

    if not all([servico_id, profissional_id, data_str]):
        return JsonResponse({'error': 'Missing required parameters'}, status=400)

    try:
        servico = Servico.objects.get(id=servico_id)
        profissional = Profissional.objects.get(id=profissional_id)
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
    except (Servico.DoesNotExist, Profissional.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    # Get existing appointments for this professional on this date with their services
    existentes = Agendamento.objects.filter(
        profissional=profissional,
        data_hora__date=data
    ).select_related('servico')

    # Generate time slots from 8:00 to 18:00
    horarios = []
    hora_inicio = datetime.combine(data, datetime.min.time().replace(hour=8))
    hora_fim = datetime.combine(data, datetime.min.time().replace(hour=18))

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

    return JsonResponse({'horarios': horarios})


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
        data_hora = datetime.strptime(data_hora_str, '%Y-%m-%dT%H:%M')

        # Check if the time slot is still available
        conflito = Agendamento.objects.filter(
            profissional=profissional,
            data_hora=data_hora
        ).exists()

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
    if hasattr(request.user, 'cliente'):
        agendamentos = Agendamento.objects.filter(
            cliente=request.user.cliente
        ).select_related('servico', 'profissional').order_by('data_hora')
        tipo = 'cliente'
    elif hasattr(request.user, 'profissional'):
        agendamentos = Agendamento.objects.filter(
            profissional=request.user.profissional
        ).select_related('servico', 'cliente').order_by('data_hora')
        tipo = 'profissional'
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
    servicos_ofertados = profissional.servico_set.all()
    todos_servicos = Servico.objects.all()

    context = {
        'profissional': profissional,
        'servicos_ofertados': servicos_ofertados,
        'todos_servicos': todos_servicos
    }
    return render(request, 'gerenciar_agenda.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_servico_ofertado(request):
    """API endpoint for professionals to add/remove services they offer"""
    if not hasattr(request.user, 'profissional'):
        return JsonResponse({'error': 'Access denied'}, status=403)

    try:
        data = json.loads(request.body)
        servico_id = data.get('servico_id')
        adicionar = data.get('adicionar', False)

        servico = Servico.objects.get(id=servico_id)
        profissional = request.user.profissional

        if adicionar:
            profissional.servico_set.add(servico)
            message = 'Service added to your offerings'
        else:
            profissional.servico_set.remove(servico)
            message = 'Service removed from your offerings'

        return JsonResponse({
            'success': True,
            'message': message
        })

    except Servico.DoesNotExist:
        return JsonResponse({'error': 'Service not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


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


def noticias(request):
    """Placeholder view for news page"""
    return render(request, 'noticias.html')


def mais(request):
    """Placeholder view for more options page"""
    return render(request, 'mais.html')