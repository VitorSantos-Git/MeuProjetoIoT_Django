# iot_core/models.py

from django.db import models
from django.utils import timezone


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


class LeituraSensor(models.Model):
    # Cria uma relação "muitos para um" com o modelo Dispositivo.
    # CASCADE significa que se o dispositivo for deletado, suas leituras também serão.
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='leituras')
    temperatura = models.DecimalField(max_digits=5, decimal_places=2, help_text="Temperatura em graus Celsius.")
    umidade = models.DecimalField(max_digits=5, decimal_places=2, help_text="Umidade relativa do ar em porcentagem.")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Data e hora da leitura do sensor.")

    def __str__(self):
        return f"Leitura de {self.dispositivo.nome} - {self.temperatura}°C ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"

    class Meta:
        verbose_name = "Leitura de Sensor"
        verbose_name_plural = "Leituras de Sensores"
        ordering = ['-timestamp'] # Ordena as leituras da mais recente para a mais antiga


class ComandoPendente(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE)
    comando = models.CharField(max_length=100)
    parametros = models.JSONField(default=dict, blank=True, null=True) # Alterado para default=dict
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_execucao_agendada = models.DateTimeField(default=timezone.now) # NOVO CAMPO: Define a data/hora agendada
    executado = models.BooleanField(default=False)
    data_execucao_real = models.DateTimeField(null=True, blank=True) # Data/hora real que foi executado

    def __str__(self):
        return f"Comando '{self.comando}' para {self.dispositivo.nome} (Agendado: {self.data_execucao_agendada.strftime('%Y-%m-%d %H:%M:%S')}, Executado: {self.executado})"




