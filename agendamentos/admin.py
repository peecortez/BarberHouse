from django.contrib import admin

from .models import Agendamento, Cliente, Profissional, Servico


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "telefone", "cpf", "usuario")
    search_fields = ("nome", "email", "cpf")


@admin.register(Profissional)
class ProfissionalAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "telefone", "cpf", "agenda_aberta")
    list_filter = ("agenda_aberta",)
    search_fields = ("nome", "email", "cpf")


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "duracao_minutos", "preco")
    search_fields = ("nome",)


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("data_hora", "cliente", "profissional", "servico", "status", "cancelado_por")
    list_filter = ("status", "data_hora")
    search_fields = ("cliente__nome", "profissional__nome", "servico__nome")
