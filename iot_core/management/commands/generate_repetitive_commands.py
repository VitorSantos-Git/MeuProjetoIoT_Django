# iot_core/management/commands/generate_repetitive_commands.py
from django.core.management.base import BaseCommand
from iot_core.models import ComandoPendente
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Gera instâncias futuras para comandos repetitivos mestres.'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando a geração de comandos repetitivos...")

        # Busca todos os comandos mestres repetitivos
        master_commands = ComandoPendente.objects.filter(is_master_repetitive=True, executado=False)

        if not master_commands.exists():
            self.stdout.write("Nenhum comando mestre repetitivo encontrado para gerar.")
            return

        for master_command in master_commands:
            # Define o período para gerar comandos: do dia seguinte até um mês no futuro.
            # Ajuste 'timedelta(days=30)' conforme a sua necessidade de "horizonte de geração".
            start_date_for_generation = timezone.localdate() + timedelta(days=1) # Começa do dia seguinte
            end_date_for_generation = start_date_for_generation + timedelta(days=30) 

            # Se o comando mestre tem uma data de fim definida, não gerar além dela
            if master_command.data_fim_repeticao and end_date_for_generation > master_command.data_fim_repeticao:
                end_date_for_generation = master_command.data_fim_repeticao

            self.stdout.write(f"\nProcessando comando mestre: '{master_command.comando}' para '{master_command.dispositivo.nome}'")
            self.stdout.write(f"  Gerando de {start_date_for_generation} até {end_date_for_generation}")
            
            # Chama o método que criamos no modelo
            generated_count = ComandoPendente.generate_repetitive_commands(
                master_command,
                start_date=start_date_for_generation,
                end_date=end_date_for_generation
            )
            self.stdout.write(f"  --> Gerou/verificou {generated_count} instâncias para este comando mestre.")
        
        self.stdout.write("\nGeração de comandos repetitivos concluída.")