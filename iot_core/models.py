# iot_core/models.py

from django.db import models
from django.utils import timezone
import json
from datetime import timedelta, date, datetime


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
    comando = models.CharField(max_length=255)
    parametros = models.JSONField(default=dict, blank=True, null=True) # Alterado para JSONField
    
    # Campos existentes para agendamento único
    data_agendamento = models.DateTimeField(auto_now_add=True) # Quando o comando foi criado/agendado no sistema
    data_execucao_agendada = models.DateTimeField() # Data/hora real que o comando deve ser executado pelo ESP
    executado = models.BooleanField(default=False)
    data_execucao_real = models.DateTimeField(null=True, blank=True) # Quando o ESP confirmou a execução

    # --- CAMPOS PARA REPETIÇÃO ---
    TIPO_REPETICAO_CHOICES = [
        ('nenhum', 'Nenhum'),
        ('diario', 'Diário'),
        ('semanal', 'Semanal'),
    ]
    # 'mensal' ou 'anual' podem ser adicionados depois

    tipo_repeticao = models.CharField(
        max_length=10,
        choices=TIPO_REPETICAO_CHOICES,
        default='nenhum',
        help_text="Define se o comando deve se repetir."
    )
    
    # Armazenará os dias da semana para repetição semanal (ex: "0,2,4" para Seg, Qua, Sex)
    # 0=Segunda, 1=Terça, ..., 6=Domingo (baseado em datetime.weekday())
    dias_da_semana = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        help_text="Dias da semana para repetição semanal (0=Seg, 1=Ter, ..., 6=Dom). Separados por vírgula."
    )

    # Data até quando a repetição deve ocorrer (opcional)
    data_fim_repeticao = models.DateField(null=True, blank=True, help_text="Data em que a repetição deve parar (opcional).")

    # Flag para identificar o "comando mestre" que gera as repetições
    # Se True, este ComandoPendente é um agendamento repetitivo e não uma instância única a ser executada.
    # Apenas instâncias geradas a partir dele (com master_command_id) são executáveis.
    is_master_repetitive = models.BooleanField(default=False, help_text="Se verdadeiro, este é um comando mestre que gera repetições.")
    
    # Campo para ligar as instâncias de repetição ao seu comando mestre
    master_command_id = models.IntegerField(null=True, blank=True, help_text="ID do comando mestre que gerou esta instância repetida.")


    def __str__(self):
        status = "Agendado"
        if self.executado:
            status = "Executado"
        elif self.data_execucao_agendada < timezone.now():
            status = "Atrasado/Não Executado" # Caso o ESP não confirme
        
        repeticao_info = ""
        if self.tipo_repeticao != 'nenhum':
            repeticao_info = f" ({self.get_tipo_repeticao_display()}"
            if self.tipo_repeticao == 'semanal' and self.dias_da_semana:
                dias_nomes = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
                dias = [dias_nomes[int(d)] for d in self.dias_da_semana.split(',') if d.strip().isdigit()]
                repeticao_info += f" em {', '.join(dias)}"
            if self.data_fim_repeticao:
                repeticao_info += f" até {self.data_fim_repeticao.strftime('%d/%m/%Y')}"
            repeticao_info += ")"

        return f"[{status}] {self.dispositivo.nome} - {self.comando} @ {self.data_execucao_agendada.strftime('%d/%m/%Y %H:%M')}{repeticao_info}"

    class Meta:
        ordering = ['data_execucao_agendada']

    @classmethod
    def generate_repetitive_commands(cls, master_command, start_date=None, end_date=None):
        """
        Gera instâncias futuras de ComandoPendente para um comando repetitivo mestre.
        master_command: A instância do ComandoPendente que é o mestre repetitivo.
        start_date: Opcional. Data de início para gerar comandos. Padrão para hoje.
        end_date: Opcional. Data de fim para gerar comandos. Padrão para master_command.data_fim_repeticao
                  ou um período futuro (ex: 30 dias).
        """
        from datetime import timedelta, date, datetime # Importa aqui para evitar circular import

        if not master_command.is_master_repetitive:
            print(f"Comando ID {master_command.id} não é um comando mestre repetitivo.")
            return

        if not start_date:
            start_date = timezone.localdate() # Começa a gerar a partir de hoje
        if not end_date:
            if master_command.data_fim_repeticao:
                end_date = master_command.data_fim_repeticao
            else:
                end_date = start_date + timedelta(days=30) # Gera para os próximos 30 dias se não houver data fim

        current_date = start_date
        generated_count = 0

        print(f"Gerando comandos repetitivos para '{master_command.comando}' ({master_command.dispositivo.nome}) de {start_date} até {end_date}...")

        while current_date <= end_date:
            # Combina a data atual com a hora agendada do comando mestre
            scheduled_datetime = timezone.make_aware(
                datetime.combine(current_date, master_command.data_execucao_agendada.time()),
                timezone.get_current_timezone() # Garante que o fuso horário seja o do projeto
            )

            # Verifica se o comando deve ser gerado para este dia
            should_generate = False
            if master_command.tipo_repeticao == 'diario':
                should_generate = True
            elif master_command.tipo_repeticao == 'semanal':
                if master_command.dias_da_semana:
                    # current_date.weekday() retorna 0 para segunda, 6 para domingo
                    # Verifica se o dia da semana atual está na lista de dias agendados
                    dias_agendados = [int(d) for d in master_command.dias_da_semana.split(',') if d.strip().isdigit()]
                    if current_date.weekday() in dias_agendados:
                        should_generate = True
                else:
                    # Se tipo é semanal mas não tem dias, não gera nada
                    should_generate = False

            if should_generate:
                # Evita gerar comandos duplicados.
                # Verifica se já existe um comando gerado para esta data/hora para o master_command.
                existing_command = ComandoPendente.objects.filter(
                    master_command_id=master_command.id,
                    data_execucao_agendada=scheduled_datetime,
                    dispositivo=master_command.dispositivo,
                    comando=master_command.comando # Para garantir que é o mesmo comando
                ).exists()

                if not existing_command:
                    # Cria uma nova instância do comando pendente
                    ComandoPendente.objects.create(
                        dispositivo=master_command.dispositivo,
                        comando=master_command.comando,
                        parametros=master_command.parametros,
                        data_execucao_agendada=scheduled_datetime,
                        executado=False,
                        is_master_repetitive=False, # Instâncias geradas NÃO são mestres
                        master_command_id=master_command.id # Liga à instância mestre
                    )
                    generated_count += 1
                    print(f"  Gerado: {master_command.comando} para {scheduled_datetime.strftime('%d/%m/%Y %H:%M')}")
                # else:
                #     print(f"  Já existe: {master_command.comando} para {scheduled_datetime.strftime('%d/%m/%Y %H:%M')}")

            current_date += timedelta(days=1) # Avança para o próximo dia

        print(f"Total de {generated_count} comandos repetitivos gerados/verificados.")
        return generated_count


class AirConditionerLog(models.Model):
    """
    Registra o estado (ligado/desligado) de um ar condicionado IoT.
    """
    device_id = models.CharField(max_length=100, help_text="ID único do dispositivo IoT (ex: MAC, serial)")
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
        ordering = ['-timestamp'] # Ordena os logs do mais recente para o mais antigo

    def __str__(self):
        return f"{self.device_id} - {self.action} em {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {'(Sucesso)' if self.success else '(Falha)'}"
    
  