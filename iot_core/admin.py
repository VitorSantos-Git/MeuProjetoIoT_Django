# iot_core/admin.py

from django.contrib import admin
from django.utils import timezone
from datetime import datetime 
from .models import Dispositivo, ComandoPendente, LeituraSensor, DeviceState, AirConditionerLog

# SEU REGISTRO EXISTENTE: DispositivoAdmin
@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ip_endereco', 'ativo', 'ultima_atualizacao')
    list_filter = ('ativo',)
    search_fields = ('nome', 'ip_endereco', 'descricao')
    # fields = ('nome', 'descricao', 'ip_endereco', 'porta', 'ativo') # Campos que você quer editar
    # readonly_fields = ('data_cadastro', 'ultima_atualizacao') # Campos somente leitura

# SEU REGISTRO EXISTENTE: ComandoPendenteAdmin
@admin.register(ComandoPendente)
class ComandoPendenteAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'comando', 'data_execucao_agendada', 'status', 'is_master_repetitive', 'tipo_repeticao')
    list_filter = ('status', 'tipo_repeticao', 'is_master_repetitive', 'dispositivo')
    search_fields = ('dispositivo__nome', 'comando', 'repetitive_command_id')
    date_hierarchy = 'data_execucao_agendada'
    # Campos que não devem ser editáveis diretamente após a criação
    readonly_fields = ('data_execucao_real',) # Pode precisar de ajustes dependendo do seu fluxo de execução

# SEU REGISTRO EXISTENTE: LeituraSensorAdmin
@admin.register(LeituraSensor)
class LeituraSensorAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'tipo_sensor', 'valor', 'unidade', 'timestamp')
    list_filter = ('dispositivo', 'tipo_sensor', 'unidade')
    search_fields = ('dispositivo__nome', 'tipo_sensor')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)

# NOVO REGISTRO ADMIN para DeviceState
@admin.register(DeviceState)
class DeviceStateAdmin(admin.ModelAdmin):
    list_display = ('device', 'is_on', 'last_updated')
    list_filter = ('is_on',)
    readonly_fields = ('last_updated',)
    search_fields = ('device__nome', 'device__ip_endereco')

# NOVO REGISTRO ADMIN para AirConditionerLog
@admin.register(AirConditionerLog)
class AirConditionerLogAdmin(admin.ModelAdmin):
    list_display = ('device_name', 'action', 'timestamp', 'success')
    list_filter = ('action', 'success', 'timestamp')
    search_fields = ('device_name', 'notes')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)