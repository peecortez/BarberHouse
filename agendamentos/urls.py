from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('', views.home, name='home'),

    # Agendamento URLs
    path('agenda-cliente/', views.agenda_cliente, name='agenda_cliente'),
    path('horarios-disponiveis/', views.horarios_disponiveis, name='horarios_disponiveis'),
    path('agendar-servico/', views.agendar_servico, name='agendar_servico'),
    path('meus-agendamentos/', views.meus_agendamentos, name='meus_agendamentos'),
    path('gerenciar-agenda/', views.gerenciar_agenda, name='gerenciar_agenda'),
    path('toggle-servico-ofertado/', views.toggle_servico_ofertado, name='toggle_servico_ofertado'),
    path('toggle-agenda-aberta/', views.toggle_agenda_aberta, name='toggle_agenda_aberta'),

    # Placeholder URLs
    path('noticias/', views.noticias, name='noticias'),
    path('mais/', views.mais, name='mais'),
]