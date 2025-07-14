# iot_core/views.py

from django.shortcuts import render, get_object_or_404, redirect # Importe get_object_or_404
from django.http import HttpResponse, JsonResponse # Importe JsonResponse
from django.views.decorators.csrf import csrf_exempt # Para desabilitar o CSRF temporariamente para a API
import json # Para lidar com JSON
from .models import Dispositivo, LeituraSensor, ComandoPendente # Importe o novo modelo LeituraSensor
from django.utils import timezone # Importe timezone para timestamps
from django.contrib import messages # Importe messages para feedback ao usuário
from datetime import datetime, timedelta, date
import pytz     
from django.conf import settings 


# Esta view retorna uma resposta HTTP simples.
def home(request):
    return HttpResponse("Olá do projeto IoT com Django! Esta é a página inicial da sua app 'iot_core'.")

@csrf_exempt # IMPORTANTE: Desabilita a proteção CSRF para esta view. Use com cautela em produção!
def receber_dados_sensor(request):
    if request.method == 'POST':
        try:
            # Tenta carregar o corpo da requisição como JSON
            data = json.loads(request.body)

            # Extrai os dados esperados do ESP8266
            device_name = data.get('dispositivo')
            temperatura = data.get('temperatura')
            umidade = data.get('umidade') # O DHT11 também fornece umidade

            # Validação básica dos dados recebidos
            if not all([device_name, temperatura is not None, umidade is not None]):
                return JsonResponse({"status": "erro", "mensagem": "Dados incompletos"}, status=400)
            
            # *** AQUI VOCÊ ADICIONARÁ A LÓGICA PARA SALVAR OS DADOS NO BANCO DE DADOS ***
            # Por enquanto, apenas vamos imprimir no console do servidor para verificar
            print(f"Dados recebidos de '{device_name}': Temperatura={temperatura}°C, Umidade={umidade}%")

            # Busca o dispositivo pelo nome
            try:
                dispositivo = Dispositivo.objects.get(nome=device_name)
                # Atualizar campos como 'ultima_atualizacao' ou 'ativo' se desejar
                # dispositivo.ultima_atualizacao = timezone.now() # Necessita 'from django.utils import timezone'
                # dispositivo.save()
            except Dispositivo.DoesNotExist:
                print(f"Dispositivo '{device_name}' não encontrado no banco de dados.")
                return JsonResponse({"status": "erro", "mensagem": "Dispositivo não registrado"}, status=404)
            
            # Cria uma nova leitura de sensor e salva no banco de dados
            LeituraSensor.objects.create(
                dispositivo=dispositivo,
                temperatura=temperatura,
                umidade=umidade,
                timestamp=timezone.now() # Usa a hora atual para o registro
            )

            # Opcional: Atualizar 'ultima_atualizacao' do dispositivo
            dispositivo.ultima_atualizacao = timezone.now()
            dispositivo.save()

            print(f"Dados salvos de '{device_name}': Temperatura={temperatura}°C, Umidade={umidade}%")
            # Retorna uma resposta de sucesso
            return JsonResponse({"status": "sucesso", "mensagem": "Dados de sensor recebidos e salvos!"}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"status": "erro", "mensagem": "JSON inválido"}, status=400)
        except Exception as e:
            # Log do erro para depuração
            print(f"Erro ao processar dados do sensor: {e}")
            return JsonResponse({"status": "erro", "mensagem": f"Erro interno do servidor: {e}"}, status=500)
    else:
        # Responde a métodos não-POST
        return JsonResponse({"status": "erro", "mensagem": "Método não permitido"}, status=405)

# view para enviar comandos ao dispositivo
@csrf_exempt # Também desabilitamos o CSRF aqui por ser uma API para o ESP8266
def enviar_comando_dispositivo(request, device_name):
    dispositivo = get_object_or_404(Dispositivo, nome=device_name)

    if request.method == 'GET':
        # ESP está pedindo um comando.
        # Buscar o comando mais antigo (agendado ou não) que AINDA NÃO FOI EXECUTADO
        # e cuja data/hora de execução agendada JÁ PASSOU ou É AGORA.
        comando_pendente = ComandoPendente.objects.filter(
            dispositivo=dispositivo,
            executado=False,
            data_execucao_agendada__lte=timezone.now() # <-- Nova condição: data agendada <= agora
        ).order_by('data_execucao_agendada').first() # Pega o mais antigo primeiro

        if comando_pendente:
            print(f"Enviando comando '{comando_pendente.comando}' para o dispositivo '{device_name}'")
            response_data = {
                "status": "sucesso",
                "comando": comando_pendente.comando,
                "parametros": json.loads(comando_pendente.parametros) if comando_pendente.parametros else {}, # Garante que seja um dict
                "dispositivo": dispositivo.nome,
                "id_comando": comando_pendente.id # Adiciona o ID do comando para o ESP poder reportar a execução
            }
            # Não marcar como executado aqui, mas esperar a confirmação do ESP via POST
        else:
            print(f"Nenhum comando pendente para o dispositivo '{device_name}'.")
            response_data = {
                "status": "sucesso",
                "comando": "NENHUM_COMANDO",
                "dispositivo": dispositivo.nome
            }
        return JsonResponse(response_data)

    elif request.method == 'POST':
        # ESP está confirmando a execução de um comando.
        try:
            data = json.loads(request.body)
            comando_id = data.get('comando_id') # Esperamos o ID do comando agora
            status_execucao = data.get('status', 'sucesso') # Status de execução reportado pelo ESP

            if comando_id:
                comando = get_object_or_404(ComandoPendente, id=comando_id, dispositivo=dispositivo)
                comando.executado = True
                comando.data_execucao_real = timezone.now() # Registra a hora real de execução
                comando.save()
                print(f"Comando ID {comando_id} '{comando.comando}' marcado como executado para '{device_name}'. Status: {status_execucao}")
                return JsonResponse({"status": "sucesso", "mensagem": "Comando marcado como executado."})
            else:
                return JsonResponse({"status": "erro", "mensagem": "ID do comando não fornecido na confirmação."}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"status": "erro", "mensagem": "JSON inválido no corpo da requisição."}, status=400)
        except Exception as e:
            print(f"Erro ao processar confirmação de comando do ESP: {e}")
            return JsonResponse({"status": "erro", "mensagem": f"Erro interno: {e}"}, status=500)
    

def gerenciar_dispositivos(request, device_name=None): # device_name agora pode ser None para a URL base
    dispositivos = Dispositivo.objects.all().order_by('nome')
    feedback_message = None
    feedback_type = None 

    if request.method == 'POST':
        # RECUPERA O NOME DO DISPOSITIVO DO CAMPO ESCONDIDO DO FORMULÁRIO
        device_name_from_post = request.POST.get('device_name_from_template')
        if not device_name_from_post:
            # Isso não deve acontecer se o campo hidden estiver sempre lá, mas é uma proteção
            feedback_message = "Erro: Nome do dispositivo não fornecido no formulário."
            feedback_type = "error"
            # Renderiza a página novamente com a mensagem de erro
            # ... (código de retorno de erro, similar ao que já temos) ...
            return # Ou renderiza o template de erro
        try:
            dispositivo = get_object_or_404(Dispositivo, nome=device_name)
            comando_str = request.POST.get('comando')
            parametros_str = request.POST.get('parametros')
            data_execucao_str = request.POST.get('data_execucao')
            
            # Novos campos de repetição
            tipo_repeticao = request.POST.get('tipo_repeticao', 'nenhum')
            dias_da_semana = request.POST.getlist('dias_da_semana') # getlist para checkboxes
            data_fim_repeticao_str = request.POST.get('data_fim_repeticao')

            # Conversão de parâmetros para JSON (se fornecido)
            parametros = {}
            if parametros_str:
                try:
                    parametros = json.loads(parametros_str)
                except json.JSONDecodeError:
                    feedback_message = "Erro: Parâmetros JSON inválidos."
                    feedback_type = "error"
                    # Renderiza a página novamente com a mensagem de erro
                    comandos_pendentes_por_dispositivo = {
                        d.id: ComandoPendente.objects.filter(dispositivo=d, executado=False).exclude(is_master_repetitive=True) 
                        for d in dispositivos
                    }
                    todos_comandos_pendentes = ComandoPendente.objects.filter(dispositivo__in=dispositivos, executado=False)
                    return render(request, 'iot_core/gerenciar_dispositivos.html', {
                        'dispositivos': dispositivos,
                        'comandos_pendentes_por_dispositivo': comandos_pendentes_por_dispositivo,
                        'todos_comandos_pendentes': todos_comandos_pendentes,
                        'feedback_message': feedback_message,
                        'feedback_type': feedback_type
                    })

            # Conversão da data de execução
            # Certifique-se de que o fuso horário está configurado em settings.py (TIME_ZONE, USE_TZ=True)
            try:
                # O input datetime-local no HTML já fornece no formato ISO 8601 (YYYY-MM-DDTHH:MM), 
                # que pode ser lido diretamente pelo datetime.fromisoformat
                data_execucao_naive = datetime.fromisoformat(data_execucao_str)
                
                # Obtém o fuso horário atual do Django (configurado em settings.py)
                current_tz = pytz.timezone(settings.TIME_ZONE) 
                
                # Torna a data/hora ciente do fuso horário
                data_execucao_aware = current_tz.localize(data_execucao_naive)

                # Validar se a data agendada não é no passado
                if data_execucao_aware < timezone.now():
                    feedback_message = "Erro: A data e hora de execução não podem ser no passado."
                    feedback_type = "error"
                     # Renderiza a página novamente com a mensagem de erro
                    comandos_pendentes_por_dispositivo = {
                        d.id: ComandoPendente.objects.filter(dispositivo=d, executado=False).exclude(is_master_repetitive=True) 
                        for d in dispositivos
                    }
                    todos_comandos_pendentes = ComandoPendente.objects.filter(dispositivo__in=dispositivos, executado=False)
                    return render(request, 'iot_core/gerenciar_dispositivos.html', {
                        'dispositivos': dispositivos,
                        'comandos_pendentes_por_dispositivo': comandos_pendentes_por_dispositivo,
                        'todos_comandos_pendentes': todos_comandos_pendentes,
                        'feedback_message': feedback_message,
                        'feedback_type': feedback_type
                    })

            except ValueError:
                feedback_message = "Erro: Formato de data e hora inválido."
                feedback_type = "error"
                 # Renderiza a página novamente com a mensagem de erro
                comandos_pendentes_por_dispositivo = {
                    d.id: ComandoPendente.objects.filter(dispositivo=d, executado=False).exclude(is_master_repetitive=True) 
                    for d in dispositivos
                }
                todos_comandos_pendentes = ComandoPendente.objects.filter(dispositivo__in=dispositivos, executado=False)
                return render(request, 'iot_core/gerenciar_dispositivos.html', {
                    'dispositivos': dispositivos,
                    'comandos_pendentes_por_dispositivo': comandos_pendentes_por_dispositivo,
                    'todos_comandos_pendentes': todos_comandos_pendentes,
                    'feedback_message': feedback_message,
                    'feedback_type': feedback_type
                })

            # Processamento da data de fim de repetição
            data_fim_repeticao_obj = None
            if data_fim_repeticao_str:
                try:
                    data_fim_repeticao_obj = datetime.strptime(data_fim_repeticao_str, '%Y-%m-%d').date()
                except ValueError:
                    feedback_message = "Erro: Formato de data de fim de repetição inválido."
                    feedback_type = "error"
                    # ... (código para renderizar com erro) ...
                    comandos_pendentes_por_dispositivo = {
                        d.id: ComandoPendente.objects.filter(dispositivo=d, executado=False).exclude(is_master_repetitive=True) 
                        for d in dispositivos
                    }
                    todos_comandos_pendentes = ComandoPendente.objects.filter(dispositivo__in=dispositivos, executado=False)
                    return render(request, 'iot_core/gerenciar_dispositivos.html', {
                        'dispositivos': dispositivos,
                        'comandos_pendentes_por_dispositivo': comandos_pendentes_por_dispositivo,
                        'todos_comandos_pendentes': todos_comandos_pendentes,
                        'feedback_message': feedback_message,
                        'feedback_type': feedback_type
                    })

            # Lógica para criar comando único ou mestre repetitivo
            if tipo_repeticao != 'nenhum':
                # É um comando repetitivo mestre
                if tipo_repeticao == 'semanal' and not dias_da_semana:
                    feedback_message = "Erro: Para repetição semanal, selecione pelo menos um dia da semana."
                    feedback_type = "error"
                     # Renderiza a página novamente com a mensagem de erro
                    comandos_pendentes_por_dispositivo = {
                        d.id: ComandoPendente.objects.filter(dispositivo=d, executado=False).exclude(is_master_repetitive=True) 
                        for d in dispositivos
                    }
                    todos_comandos_pendentes = ComandoPendente.objects.filter(dispositivo__in=dispositivos, executado=False)
                    return render(request, 'iot_core/gerenciar_dispositivos.html', {
                        'dispositivos': dispositivos,
                        'comandos_pendentes_por_dispositivo': comandos_pendentes_por_dispositivo,
                        'todos_comandos_pendentes': todos_comandos_pendentes,
                        'feedback_message': feedback_message,
                        'feedback_type': feedback_type
                    })
                
                # Cria o comando mestre (que não será executado diretamente pelo ESP)
                master_command = ComandoPendente.objects.create(
                    dispositivo=dispositivo,
                    comando=comando_str,
                    parametros=parametros,
                    data_execucao_agendada=data_execucao_aware,
                    is_master_repetitive=True, # MARCA COMO MESTRE
                    tipo_repeticao=tipo_repeticao,
                    dias_da_semana=','.join(dias_da_semana) if dias_da_semana else None,
                    data_fim_repeticao=data_fim_repeticao_obj
                )
                
                feedback_message = f"Comando '{comando_str}' agendado como REPETITIVO para '{dispositivo.nome}' com sucesso!"
                feedback_type = "success"

                # Chamar a função para gerar as primeiras instâncias (ex: para hoje e alguns dias/semanas)
                # Começa a gerar a partir da data de agendamento do mestre, mas apenas para o dia *futuro* se a hora já passou.
                # A tarefa agendada vai cuidar da geração contínua.
                
                # Se a data_execucao_aware for no futuro, a primeira instância será gerada por ela mesma.
                # Se for no passado (e.g. "todo dia as 23h00"), então a primeira geração deve ser para HOJE se a hora não passou,
                # ou para AMANHÃ se a hora já passou.
                
                # Para simplificar, vamos deixar que o comando `generate_repetitive_commands` cuide da geração futura
                # Este agendamento mestre apenas cria o "template".
                # Para garantir que o comando de hoje (se aplicável) seja gerado:
                # Verifique se a data de execução agendada está no futuro (hora do dia de hoje).
                # Se a data agendada for para um dia no futuro (ex: agendou para semana que vem),
                # o comando mestre já vai indicar isso.
                # A geração principal deve ser feita pelo comando de gerenciamento.
                
                # Podemos chamar a geração para o dia de hoje APENAS se a hora ainda não passou:
                # E se a data agendada é hoje
                if data_execucao_aware.date() == timezone.localdate() and data_execucao_aware > timezone.now():
                    # Gerar apenas a instância para hoje, se ela ainda não passou
                    ComandoPendente.generate_repetitive_commands(master_command, start_date=timezone.localdate(), end_date=timezone.localdate())
                elif data_execucao_aware.date() < timezone.localdate():
                     # Se agendou um comando repetitivo mestre com data/hora no passado,
                     # não gerar para hoje, deixe o agendador gerar para o futuro.
                     pass 
                # Se data_execucao_aware.date() for amanhã ou depois, o agendador cuidará.

            else:
                # É um comando único (comportamento atual)
                ComandoPendente.objects.create(
                    dispositivo=dispositivo,
                    comando=comando_str,
                    parametros=parametros,
                    data_execucao_agendada=data_execucao_aware,
                    is_master_repetitive=False # Comando único
                )
                feedback_message = f"Comando '{comando_str}' agendado para '{dispositivo.nome}' em {data_execucao_aware.strftime('%d/%m/%Y %H:%M')} com sucesso!"
                feedback_type = "success"

        except Exception as e:
            feedback_message = f"Ocorreu um erro ao agendar o comando: {e}"
            feedback_type = "error"
            print(f"Erro ao agendar comando: {e}") # Para depuração no console
        """ 
        # Re-renderiza a página com os dados atualizados e feedback
        comandos_pendentes_por_dispositivo = {
            d.id: ComandoPendente.objects.filter(dispositivo=d, executado=False).exclude(is_master_repetitive=True) 
            for d in dispositivos
        }"""

       # Re-renderiza a página com os dados atualizados e feedback
        comandos_pendentes_por_dispositivo = {}
        comandos_mestres_por_dispositivo = {}

        for d in dispositivos:
            # Comandos únicos executáveis
            comandos_pendentes_por_dispositivo[d.id] = ComandoPendente.objects.filter(
                dispositivo=d, 
                executado=False, 
                is_master_repetitive=False
            ).order_by('data_execucao_agendada') # Adiciona ordenação

            # Comandos mestres repetitivos
            comandos_mestres_por_dispositivo[d.id] = ComandoPendente.objects.filter(
                dispositivo=d, 
                is_master_repetitive=True, 
                executado=False # Um comando mestre nunca é "executado" no ESP, mas podemos marcar se ele foi "desativado"
            ).order_by('data_execucao_agendada') # Adiciona ordenação
            
        return render(request, 'iot_core/gerenciar_dispositivos.html', {
            'dispositivos': dispositivos,
            'comandos_pendentes_por_dispositivo': comandos_pendentes_por_dispositivo,
            'comandos_mestres_por_dispositivo': comandos_mestres_por_dispositivo, # NOVO CONTEXTO
            'feedback_message': feedback_message,
            'feedback_type': feedback_type
        })
    else:
        # GET request: apenas exibe os dispositivos e comandos
        comandos_pendentes_por_dispositivo = {}
        comandos_mestres_por_dispositivo = {} # NOVO DICIONÁRIO

        for d in dispositivos:
            # Comandos únicos executáveis
            comandos_pendentes_por_dispositivo[d.id] = ComandoPendente.objects.filter(
                dispositivo=d, 
                executado=False, 
                is_master_repetitive=False
            ).order_by('data_execucao_agendada')

            # Comandos mestres repetitivos
            comandos_mestres_por_dispositivo[d.id] = ComandoPendente.objects.filter(
                dispositivo=d, 
                is_master_repetitive=True, 
                executado=False # Um comando mestre nunca é "executado" no ESP
            ).order_by('data_execucao_agendada')
        
        return render(request, 'iot_core/gerenciar_dispositivos.html', {
            'dispositivos': dispositivos,
            'comandos_pendentes_por_dispositivo': comandos_pendentes_por_dispositivo,
            'comandos_mestres_por_dispositivo': comandos_mestres_por_dispositivo, # NOVO CONTEXTO
            'feedback_message': feedback_message,
            'feedback_type': feedback_type
        })






