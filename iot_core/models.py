# iot_core/models.py

from django.db import models
from django.utils import timezone
import json
from datetime import timedelta, date, datetime

# SEU MODELO EXISTENTE: Dispositivo
class Dispositivo(models.Model):
    nome = models.CharField(max_length=100, unique=True, help_text="Nome único para identificar o dispositivo (ex: 'ESP8266_Sala').")
    descricao = models.TextField(blank=True, null=True, help_text="Descrição opcional do dispositivo e sua localização.")
    ip_endereco = models.GenericIPAddressField(unique=True, help_text="Endereço IP do dispositivo na rede local.")
    porta = models.IntegerField(default=80, help_text="Porta HTTP que o dispositivo está escutando (geralmente 80).")
    ativo = models.BooleanField(default=True, help_text="Indica se o dispositivo está ativo e online.")
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Dispositivo IoT"
        verbose_name_plural = "Dispositivos IoT"
        ordering = ['nome']


# SEU MODELO EXISTENTE: ComandoPendente
class ComandoPendente(models.Model):
    STATUS_CHOICES = [
        ('AGENDADO', 'Agendado'),
        ('EXECUTADO', 'Executado'),
        ('FALHOU', 'Falhou'),
        ('ATRASADO', 'Atrasado/Não Executado'),
    ]
    TIPO_REPETICAO_CHOICES = [
        ('NENHUM', 'Nenhum'),
        ('DIARIO', 'Diário'),
        ('SEMANAL', 'Semanal'),
        # Adicione outros tipos de repetição conforme necessário
    ]

    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, help_text="O dispositivo para o qual o comando é destinado.")
    comando = models.CharField(max_length=50, help_text="O comando a ser enviado (ex: 'BUZZER_ON', 'LED_OFF', 'RELE_ON', 'RELE_OFF').")
    data_execucao_agendada = models.DateTimeField(help_text="Data e hora em que o comando deve ser executado.")
    data_execucao_real = models.DateTimeField(blank=True, null=True, help_text="Data e hora real da execução do comando.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='AGENDADO', help_text="Status atual do comando.")
    is_master_repetitive = models.BooleanField(default=False, help_text="Indica se é um comando mestre para repetição (visível no Admin).")
    tipo_repeticao = models.CharField(max_length=10, choices=TIPO_REPETICAO_CHOICES, default='NENHUM', help_text="Tipo de repetição do comando.")
    
    # Adicionando um campo para identificar o comando repetitivo (para o agendamento de comandos secundários)
    repetitive_command_id = models.CharField(max_length=100, blank=True, null=True, unique=True,
                                            help_text="ID único para comandos repetitivos mestre.")

    def __str__(self):
        status_display = dict(self.STATUS_CHOICES).get(self.status, self.status)
        repeticao_display = dict(self.TIPO_REPETICAO_CHOICES).get(self.tipo_repeticao, self.tipo_repeticao)
        return f"[{status_display}] {self.dispositivo.nome} - {self.comando} @ {self.data_execucao_agendada.strftime('%d/%m/%Y %H:%M')} ({repeticao_display})"

    class Meta:
        verbose_name = "Comando Pendente"
        verbose_name_plural = "Comandos Pendentes"
        ordering = ['data_execucao_agendada']


# SEU MODELO EXISTENTE: LeituraSensor
class LeituraSensor(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, help_text="O dispositivo que enviou a leitura.")
    tipo_sensor = models.CharField(max_length=50, null=True, blank=True, help_text="Tipo de sensor (ex: 'Temperatura', 'Umidade', 'Luminosidade').")
    valor = models.FloatField(null=True, blank=True, help_text="Valor lido pelo sensor.")
    unidade = models.CharField(max_length=10, blank=True, null=True, help_text="Unidade da leitura (ex: '°C', '%', 'lux').")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Data e hora da leitura.")

    def __str__(self):
        return f"{self.dispositivo.nome} - {self.tipo_sensor}: {self.valor}{self.unidade or ''} @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        verbose_name = "Leitura de Sensor"
        verbose_name_plural = "Leituras de Sensores"
        ordering = ['-timestamp']


# NOVO MODELO: Estado Atual do Dispositivo (usando seu Dispositivo)
class DeviceState(models.Model):
    """
    Registra o estado atual de um dispositivo IoT.
    """
    device = models.OneToOneField(Dispositivo, on_delete=models.CASCADE, primary_key=True, help_text="O dispositivo IoT associado a este estado.")
    is_on = models.BooleanField(default=False, help_text="True se o dispositivo estiver ligado, False se estiver desligado.")
    last_updated = models.DateTimeField(auto_now=True, help_text="Última vez que o estado foi atualizado.")

    class Meta:
        verbose_name = "Estado do Dispositivo"
        verbose_name_plural = "Estados dos Dispositivos"

    def __str__(self):
        return f"{self.device.nome} está {'LIGADO' if self.is_on else 'DESLIGADO'}"

# NOVO MODELO: Log de Ações de Ar Condicionado (usando o nome do dispositivo como identificador no log)
class AirConditionerLog(models.Model):
    """
    Registra o estado (ligado/desligado) de um ar condicionado IoT.
    """
    # Usaremos o nome do Dispositivo como identificador aqui
    device_name = models.CharField(max_length=100, null=True, blank=True, help_text="Nome do dispositivo IoT (ex: Ar Sala, Ar Quarto)")
    action = models.CharField(
        max_length=10,
        choices=[('LIGAR', 'Ligar'), ('DESLIGAR', 'Desligar')],
        help_text="Ação executada no ar condicionado"
    )
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Data e hora da ação")
    success = models.BooleanField(default=True, help_text="Indica se a ação foi bem-sucedida")
    notes = models.TextField(blank=True, null=True, help_text="Observações adicionais (ex: erro, motivo)")

    class Meta:
        verbose_name = "Log do Ar Condicionado"
        verbose_name_plural = "Logs do Ar Condicionado"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.device_name} - {self.action} em {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {'(Sucesso)' if self.success else '(Falha)'}"