from django.contrib import admin

from .models import Agendamento, Avaliacao, Cliente, EmailEnviado, Profissional, Servico


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
    list_display = ("data_hora", "cliente", "profissional", "servico", "status", "cancelado_por", "lembrete_enviado_em")
    list_filter = ("status", "data_hora")
    search_fields = ("cliente__nome", "profissional__nome", "servico__nome")


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "nota", "profissional", "cliente", "comentario")
    list_filter = ("nota",)
    search_fields = ("agendamento__profissional__nome", "agendamento__cliente__nome", "comentario")

    @admin.display(description="Profissional")
    def profissional(self, obj):
        return obj.agendamento.profissional.nome

    @admin.display(description="Cliente")
    def cliente(self, obj):
        return obj.agendamento.cliente.nome


@admin.register(EmailEnviado)
class EmailEnviadoAdmin(admin.ModelAdmin):
    """Historico de envios: mostra quanto do teto diario ja foi usado."""
    list_display = ("enviado_em", "tipo", "destinatario", "assunto", "sucesso")
    list_filter = ("tipo", "sucesso", "enviado_em")
    search_fields = ("destinatario",)
