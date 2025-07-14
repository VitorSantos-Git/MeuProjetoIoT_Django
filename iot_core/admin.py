# iot_core/admin.py

from django.contrib import admin
from .models import Dispositivo, LeituraSensor, ComandoPendente  # Importe o seu modelo Dispositivo
from django.utils import timezone
from datetime import datetime 


# Registre o modelo Dispositivo se ainda não o fez
@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao', 'ultima_atualizacao')
    search_fields = ('nome',)

# Crie uma classe Admin customizada para ComandoPendente
@admin.register(ComandoPendente)
class ComandoPendenteAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'comando', 'data_execucao_agendada', 'executado', 'data_execucao_real', 'is_master_repetitive', 'tipo_repeticao')
    list_filter = ('executado', 'is_master_repetitive', 'tipo_repeticao', 'dispositivo')
    search_fields = ('comando', 'parametros', 'dispositivo__nome')
    date_hierarchy = 'data_execucao_agendada' # Ajuda na navegação por data

    # Adicione campos para o formulário de adição/edição no Admin
    fieldsets = (
        (None, {
            'fields': ('dispositivo', 'comando', 'parametros', 'data_execucao_agendada')
        }),
        ('Configurações de Repetição', {
            'fields': ('is_master_repetitive', 'tipo_repeticao', 'dias_da_semana', 'data_fim_repeticao'),
            'classes': ('collapse',), # Opcional: faz a seção ser recolhível
        }),
        ('Status de Execução', {
            'fields': ('executado', 'data_execucao_real'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Este método é chamado quando um objeto ComandoPendente é salvo no Admin.

        # Se a data_execucao_agendada não for aware, torne-a aware no fuso horário do projeto.
        # Isso é crucial para garantir que os dados sejam salvos corretamente em UTC pelo Django.
        if obj.data_execucao_agendada and timezone.is_naive(obj.data_execucao_agendada):
            # O Django Admin geralmente pega o input datetime-local como naive.
            # Tornamos ele aware no TIME_ZONE do settings.
            obj.data_execucao_agendada = timezone.make_aware(
                obj.data_execucao_agendada, 
                timezone.get_current_timezone()
            )


        # Chame o método save_model original para realmente salvar o objeto
        super().save_model(request, obj, form, change)

    # Se você tiver um filtro 'split_and_map_weekday_names', ele precisaria ser importado
    # ou a lógica para 'dias_da_semana' no Admin talvez precise de um custom widget/field.
    # Por enquanto, focamos na data/hora.
