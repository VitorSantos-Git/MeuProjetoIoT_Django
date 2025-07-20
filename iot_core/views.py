# iot_core/views.py

from django.shortcuts import render, get_object_or_404, redirect # Importe get_object_or_404
from django.http import HttpResponse, JsonResponse # Importe JsonResponse
from django.views.decorators.csrf import csrf_exempt # Para desabilitar o CSRF temporariamente para a API
import json # Para lidar com JSON
from .models import Dispositivo, LeituraSensor, ComandoPendente # Importe o novo modelo LeituraSensor
from django.utils import timezone # Importe timezone para timestamps
from django.contrib import messages # Importe messages para feedback ao usuário
from datetime import datetime, timedelta, date
from django.utils.timezone import get_current_timezone
import pytz     
from django.conf import settings 

from django.views.decorators.http import require_POST
import requests # Para fazer requisições HTTP para o ESP8266
import logging


from .models import Dispositivo, DeviceState, AirConditionerLog # Importa Dispositivo
from .DispositivoForm import DispositivoForm # Importa DispositivoForm

logger = logging.getLogger(__name__) # Para logar erros/informações


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
            # Campo 'executado' foi removido e substituído por 'status'.
            # Usamos 'status' para identificar comandos pendentes.
            status='AGENDADO', # <--- CORREÇÃO AQUI: Usar 'status' em vez de 'executado'
            data_execucao_agendada__lte=timezone.now() # <-- Nova condição: data agendada <= agora
        ).order_by('data_execucao_agendada').first() # Pega o mais antigo primeiro

        if comando_pendente:
            print(f"Enviando comando '{comando_pendente.comando}' para o dispositivo '{device_name}'")
            response_data = {
                "status": "sucesso",
                "comando": comando_pendente.comando,
                # Removendo 'parametros' daqui. Se você removeu o campo 'parametros' do modelo ComandoPendente
                # como indicado na saída do makemigrations, esta linha causaria um AttributeError.
                # Se o campo 'parametros' AINDA EXISTE, mantenha-o.
                # Pela sua saída do makemigrations, 'parametros' FOI REMOVIDO.
                # Se você realmente precisa de parâmetros, precisará reintroduzi-los no modelo e migrar.
                # Por enquanto, vou COMENTAR/REMOVER esta linha para evitar outro erro.
                # "parametros": json.loads(comando_pendente.parametros) if comando_pendente.parametros else {}, # Garante que seja um dict
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
            status_execucao = data.get('status_execucao', 'sucesso') # <--- Mudei para 'status_execucao' para evitar conflito com campo 'status' do modelo
            
            if comando_id:
                comando = get_object_or_404(ComandoPendente, id=comando_id, dispositivo=dispositivo)
                
                # Campo 'executado' foi removido. Agora atualizamos o campo 'status'.
                # Baseado no 'status_execucao' recebido do ESP, definimos o status do comando.
                if status_execucao == 'sucesso':
                    comando.status = 'EXECUTADO' # <--- CORREÇÃO AQUI: Usar 'status' em vez de 'executado'
                else:
                    comando.status = 'FALHOU' # Ou outro status apropriado para falha
                
                comando.data_execucao_real = timezone.now() # Registra a hora real de execução
                comando.save()
                print(f"Comando ID {comando_id} '{comando.comando}' marcado com status '{comando.status}' para '{device_name}'.")
                
                # Se este for um comando mestre repetitivo, agendar o próximo
                if comando.is_master_repetitive:
                    # Chame a função de agendamento do próximo comando aqui
                    # Exemplo: agendar_proximo_comando_repetitivo(comando)
                    print(f"Comando mestre repetitivo concluído. Próximo agendamento necessário.")
                    # Você precisará implementar a lógica de agendamento aqui ou chamar uma função helper.
                    # Por exemplo, uma função para criar a próxima instância do comando agendado.
                    # Isso dependeria da sua lógica para 'DIARIO', 'SEMANAL', etc.

                return JsonResponse({"status": "sucesso", "mensagem": "Comando marcado como executado/falho."})
            else:
                return JsonResponse({"status": "erro", "mensagem": "ID do comando não fornecido na confirmação."}, status=400)

        except json.JSONDecodeError:
            print(f"Erro: JSON inválido no corpo da requisição POST do ESP.")
            return JsonResponse({"status": "erro", "mensagem": "JSON inválido no corpo da requisição."}, status=400)
        except ComandoPendente.DoesNotExist:
            print(f"Erro: ComandoPendete ID {data.get('comando_id')} não encontrado para {device_name}.")
            return JsonResponse({"status": "erro", "mensagem": "Comando não encontrado para atualização."}, status=404)
        except Exception as e:
            print(f"Erro inesperado ao processar confirmação de comando do ESP para {device_name}: {e}")
            return JsonResponse({"status": "erro", "mensagem": f"Erro interno: {e}"}, status=500)
    
    # Se o método não for GET nem POST
    return JsonResponse({"status": "erro", "mensagem": "Método de requisição não permitido."}, status=405)


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
                data_execucao_str = request.POST.get('data_execucao')
                data_execucao_naive = datetime.fromisoformat(data_execucao_str)
                
                # Obtém o fuso horário atual do Django (configurado em settings.py)
                current_tz = pytz.timezone(settings.TIME_ZONE) 
                
                # Torna a data/hora ciente do fuso horário
                data_execucao_aware = timezone.make_aware(data_execucao_naive, timezone.get_current_timezone())

          
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


# View para exibir a dashboard de dispositivos IoT
def device_dashboard(request):
    # Pega todos os dispositivos ativos
    devices = Dispositivo.objects.filter(ativo=True)
    
    devices_data = [] # Lista para armazenar todos os dados que serão passados para o template

    for device in devices:
        # Pega o estado atual do dispositivo ou cria um novo se não existir
        device_state, created = DeviceState.objects.get_or_create(device=device)

        # Obter a última leitura de TEMPERATURA para este dispositivo
        ultima_temperatura_leitura = LeituraSensor.objects.filter(
            dispositivo=device, # Usamos 'device' da iteração
            tipo_sensor='Temperatura' # OU 'temperatura', verifique o que seu ESP envia
        ).order_by('-timestamp').first()

        # Obter a última leitura de UMIDADE para este dispositivo
        ultima_umidade_leitura = LeituraSensor.objects.filter(
            dispositivo=device, # Usamos 'device' da iteração
            tipo_sensor='Umidade' # OU 'umidade', verifique o que seu ESP envia
        ).order_by('-timestamp').first()

        # Formata as leituras, verificando se a leitura existe antes de acessar .valor ou .unidade
        formatted_temperatura = 'N/A'
        if ultima_temperatura_leitura:
            formatted_temperatura = f"{ultima_temperatura_leitura.valor}{ultima_temperatura_leitura.unidade or '°C'}" # Adicionei um default para unidade

        formatted_umidade = 'N/A'
        if ultima_umidade_leitura:
            formatted_umidade = f"{ultima_umidade_leitura.valor}{ultima_umidade_leitura.unidade or '%'}" # Adicionei um default para unidade

        devices_data.append({
            'obj': device,
            'current_state': device_state, # Passa o objeto DeviceState
            'ultima_temperatura': formatted_temperatura,
            'ultima_umidade': formatted_umidade,
            'is_on': device_state.is_on, # Redundante com current_state.is_on, mas mantido para clareza no template
        })
    
    form = DispositivoForm() # Formulário para adicionar novo dispositivo

    context = {
        'devices_data': devices_data, # Renomeei para evitar conflito e ser mais descritivo
        'form': form,
        'mensagem': 'Bem-vindo ao dashboard interativo dos seus dispositivos IoT!' # Mensagem geral
    }
    
    return render(request, 'iot_core/device_dashboard.html', context)





# View para adicionar um novo dispositivo IoT
@require_POST
def add_device(request):
    form = DispositivoForm(request.POST) # Usa DispositivoForm
    if form.is_valid():
        device = form.save()
        # Ao adicionar um novo dispositivo, inicialize seu estado como desligado
        DeviceState.objects.get_or_create(device=device, defaults={'is_on': False})
        messages.success(request, f'Dispositivo "{device.nome}" adicionado com sucesso!')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                # CORREÇÃO DA INDENTAÇÃO E REMOÇÃO DA LINHA INCORRETA
                error_message_prefix = ''
                if field == "__all__":
                    error_message_prefix = 'Erro geral: '
                
                # Esta é a linha correta, com a indentação ajustada
                messages.error(request, f'Erro no campo {field}: {error_message_prefix}{error}')
                
                # REMOVA A LINHA ABAIXO (era a linha com o SyntaxError)
                # messages.error(request, f'Erro no campo {field}: {% if field == "__all__" %}Erro geral: {% endif %}{error}') # Mensagem mais clara
                
    return redirect('device_dashboard')


# View para remover um dispositivo IoT
@require_POST
def delete_device(request, device_id): # device_id aqui é a PK do Dispositivo
    device = get_object_or_404(Dispositivo, pk=device_id) # Busca pelo PK
    device_name = device.nome
    device.delete()
    messages.info(request, f'Dispositivo "{device_name}" removido.')
    return redirect('device_dashboard')


# View para enviar comando ON/OFF
# iot_core/views.py

# ... (imports)

@csrf_exempt
@require_POST
def send_command(request):
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id') # <--- Aqui ele espera o ID do dispositivo
        command_type = data.get('command')

        if not device_id or not command_type:
            return JsonResponse({'status': 'erro', 'message': 'ID do dispositivo ou tipo de comando ausente.'}, status=400)

        dispositivo = get_object_or_404(Dispositivo, pk=device_id) # <--- Ele busca pelo ID (pk)

        # Crie um novo ComandoPendente
        ComandoPendente.objects.create(
            dispositivo=dispositivo,
            comando=command_type,
            tipo_repeticao='UNICA',
            data_execucao_agendada=timezone.now(),
            status='AGENDADO'
        )
        logger.info(f"Comando '{command_type}' agendado para o dispositivo '{dispositivo.nome}'.")
        return JsonResponse({'status': 'sucesso', 'message': 'Comando agendado com sucesso!'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'erro', 'message': 'Corpo da requisição inválido (JSON esperado).'}, status=400)
    except Dispositivo.DoesNotExist:
        # O erro que você está vendo!
        print(f"Erro: Dispositivo com ID {device_id} não encontrado ao tentar agendar comando.")
        return JsonResponse({'status': 'erro', 'message': 'Dispositivo não encontrado.'}, status=404)
    except Exception as e:
        logger.exception(f"Erro ao agendar comando: {e}")
        return JsonResponse({'status': 'erro', 'message': str(e)}, status=500)

# NOVA View: Endpoint para o ESP8266 buscar comandos pendentes
def get_device_command(request, device_name):
    try:
        device = get_object_or_404(Dispositivo, nome=device_name)
        
        # Tenta encontrar o comando AGENDADO mais antigo para este dispositivo
        # Que não seja um comando mestre de repetição (isso é para agendamento manual)
        command_to_execute = ComandoPendente.objects.filter(
            dispositivo=device, 
            status='AGENDADO'
        ).order_by('data_execucao_agendada').first()

        if command_to_execute:
            # Marca o comando como EXECUTADO (ou PENDENTE_EXECUTANDO se quiser um estado intermediário)
            # É importante que o ESP envie a confirmação final!
            # Por enquanto, vamos marcá-lo como EXECUTADO aqui para que não seja pego novamente imediatamente.
            # O ESP ainda precisa enviar a confirmação para marcar como EXECUTADO/FALHOU.
            # Vamos mudar isso: o ESP vai puxar e depois fazer um POST para atualizar o status.
            # Por isso, apenas retornamos o comando aqui.

            response_data = {
                'status': 'sucesso',
                'comando': command_to_execute.comando,
                'id_comando': command_to_execute.id,
                # 'parametros': {} # Se você tiver parâmetros adicionais no ComandoPendente
            }
            logger.info(f"Comando '{command_to_execute.comando}' enviado para {device_name}.")
            return JsonResponse(response_data)
        else:
            return JsonResponse({'status': 'sucesso', 'comando': 'NENHUM_COMANDO', 'id_comando': 0})
            
    except Dispositivo.DoesNotExist:
        return JsonResponse({'status': 'erro', 'message': 'Dispositivo não encontrado.'}, status=404)
    except Exception as e:
        logger.exception(f"Erro ao buscar comandos para {device_name}: {e}")
        return JsonResponse({'status': 'erro', 'message': str(e)}, status=500)


# NOVA View: Endpoint para o ESP8266 atualizar o status de um comando
@csrf_exempt
@require_POST
def update_command_status(request):
    try:
        data = json.loads(request.body)
        comando_id = data.get('comando_id')
        status_msg = data.get('status') # Ex: 'EXECUTADO', 'FALHOU', 'ATRASADO'

        if not comando_id or not status_msg:
            return JsonResponse({'status': 'erro', 'message': 'Dados incompletos.'}, status=400)

        command_obj = get_object_or_404(ComandoPendente, pk=comando_id)
        
        # Validar status_msg contra ComandoPendente.STATUS_CHOICES
        valid_statuses = [choice[0] for choice in ComandoPendente.STATUS_CHOICES]
        if status_msg not in valid_statuses:
            return JsonResponse({'status': 'erro', 'message': 'Status inválido.'}, status=400)

        command_obj.status = status_msg
        command_obj.data_execucao_real = timezone.now() # Atualiza a hora da execução real
        command_obj.save()

        # Opcional: Atualizar o DeviceState e logar se for um comando de LIGAR/DESLIGAR AR
        if command_obj.comando in ["LIGAR_AR", "DESLIGAR_AR"]:
            device_state, created = DeviceState.objects.get_or_create(device=command_obj.dispositivo)
            if status_msg == "EXECUTADO":
                device_state.is_on = (command_obj.comando == "LIGAR_AR")
                device_state.save()
            
            # Registrar no AirConditionerLog o resultado final
            AirConditionerLog.objects.create(
                device_name=command_obj.dispositivo.nome,
                action="LIGAR" if command_obj.comando == "LIGAR_AR" else "DESLIGAR",
                success=(status_msg == "EXECUTADO"),
                notes=f"Comando via ESP: {status_msg}"
            )

        logger.info(f"Comando ID {comando_id} para {command_obj.dispositivo.nome} atualizado para {status_msg}.")
        return JsonResponse({'status': 'sucesso', 'message': 'Status do comando atualizado.'})
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'erro', 'message': 'Corpo da requisição inválido (JSON esperado).'}, status=400)
    except ComandoPendente.DoesNotExist:
        return JsonResponse({'status': 'erro', 'message': 'Comando não encontrado.'}, status=404)
    except Exception as e:
        logger.exception(f"Erro ao atualizar status do comando: {e}")
        return JsonResponse({'status': 'erro', 'message': str(e)}, status=500)
    


@csrf_exempt
@require_POST
def receive_sensor_data(request):
    try:
        data = json.loads(request.body)
        device_name = data.get('dispositivo')
        temperatura = data.get('temperatura')
        umidade = data.get('umidade')

        if not device_name:
            return JsonResponse({'status': 'erro', 'message': 'Nome do dispositivo ausente.'}, status=400)

        dispositivo = get_object_or_404(Dispositivo, nome=device_name) # <- Aqui ele busca pelo NOME do dispositivo, não ID

        # Criar leitura para TEMPERATURA, se disponível
        if temperatura is not None:
            LeituraSensor.objects.create(
                dispositivo=dispositivo,
                tipo_sensor='Temperatura', # <-- Tipo de sensor. Precisa ser 'Temperatura'
                valor=temperatura,
                unidade='°C'
            )

        # Criar leitura para UMIDADE, se disponível
        if umidade is not None:
            LeituraSensor.objects.create(
                dispositivo=dispositivo,
                tipo_sensor='Umidade', # <-- Tipo de sensor. Precisa ser 'Umidade'
                valor=umidade,
                unidade='%'
            )

        print(f"Dados do sensor recebidos: {data}")

        return JsonResponse({'status': 'sucesso', 'message': 'Dados do sensor recebidos e salvos.'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'erro', 'message': 'Corpo da requisição inválido (JSON esperado).'}, status=400)
    except Dispositivo.DoesNotExist:
        # Este erro significa que o 'device_name' enviado pelo ESP não corresponde a nenhum dispositivo cadastrado
        print(f"Erro: Dispositivo '{device_name}' não encontrado ao receber dados do sensor.")
        return JsonResponse({'status': 'erro', 'message': f'Dispositivo "{device_name}" não encontrado.'}, status=404)
    except Exception as e:
        logger.exception(f"Erro ao receber dados do sensor: {e}")
        return JsonResponse({'status': 'erro', 'message': str(e)}, status=500)
