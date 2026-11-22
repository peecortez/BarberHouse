from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .forms import RecuperarSenhaForm

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('confirmar-email/<str:token>/', views.confirmar_email, name='confirmar_email'),
    path('reenviar-confirmacao/', views.reenviar_confirmacao, name='reenviar_confirmacao'),
    path('', views.home, name='home'),

    # Recuperar senha (views prontas do Django, com as telas e o e-mail da BarberHouse)
    path('recuperar-senha/', auth_views.PasswordResetView.as_view(
        template_name='recuperar_senha.html',
        form_class=RecuperarSenhaForm,
    ), name='password_reset'),
    path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='recuperar_senha_enviado.html',
    ), name='password_reset_done'),
    path('redefinir-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='redefinir_senha.html',
    ), name='password_reset_confirm'),
    path('redefinir-senha/concluido/', auth_views.PasswordResetCompleteView.as_view(
        template_name='redefinir_senha_concluido.html',
    ), name='password_reset_complete'),

    # Agendamento URLs
    path('agenda-cliente/', views.agenda_cliente, name='agenda_cliente'),
    path('horarios-disponiveis/', views.horarios_disponiveis, name='horarios_disponiveis'),
    path('agendar-servico/', views.agendar_servico, name='agendar_servico'),
    path('meus-agendamentos/', views.meus_agendamentos, name='meus_agendamentos'),
    path('gerenciar-agenda/', views.gerenciar_agenda, name='gerenciar_agenda'),
    path('toggle-agenda-aberta/', views.toggle_agenda_aberta, name='toggle_agenda_aberta'),
    path('agendamento/<int:agendamento_id>/status/', views.atualizar_status, name='atualizar_status'),
    path('agendamento/<int:agendamento_id>/avaliar/', views.avaliar_atendimento, name='avaliar_atendimento'),
    # Placeholder URLs
    path('noticias/', views.noticias, name='noticias'),
    path('noticias/resgatar-cupom/', views.resgatar_cupom, name='resgatar_cupom'),
    path('sobre/', views.sobre, name='sobre'),
]
