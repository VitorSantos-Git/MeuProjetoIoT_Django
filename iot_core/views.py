# iot_core/views.py

from django.shortcuts import render, get_object_or_404, redirect # Importe get_object_or_404
from django.http import HttpResponse, JsonResponse # Importe JsonResponse
from django.views.decorators.csrf import csrf_exempt # Para desabilitar o CSRF temporariamente para a API
import json # Para lidar com JSON
from .models import Dispositivo, LeituraSensor, ComandoPendente # Importe o novo modelo LeituraSensor
from django.utils import timezone # Importe timezone para timestamps
from django.contrib import messages # Importe messages para feedback ao usuário
import datetime #
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
    

def gerenciar_dispositivos(request):
    if request.method == 'POST':
        device_id = request.POST.get('device_id')
        comando_texto = request.POST.get('comando')
        parametros_json = request.POST.get('parametros', '').strip()

        # Novas entradas do formulário: data e hora
        data_agendamento_str = request.POST.get('data_agendamento')
        hora_agendamento_str = request.POST.get('hora_agendamento')

        # Se os parâmetros estiverem vazios após remover espaços, trate como JSON vazio
        if not parametros_json:
            parametros_json = '{}'

        dispositivo = get_object_or_404(Dispositivo, id=device_id)

        try:
            parametros_parsed = json.loads(parametros_json)
            if not isinstance(parametros_parsed, dict):
                raise ValueError("Parâmetros devem ser um JSON válido (objeto), ex: {'chave': 'valor'}.")

            # **Processamento da data e hora agendada**
            # Combina a data e a hora do formulário em uma string datetime
            datetime_str = f"{data_agendamento_str} {hora_agendamento_str}"
            # Converte a string para um objeto datetime
            # O formato é 'YYYY-MM-DD HH:MM'
            agendamento_local_dt = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')

            # Obtém o fuso horário configurado no Django settings (ex: 'America/Sao_Paulo')
            django_timezone = pytz.timezone(settings.TIME_ZONE)

            # Torna o objeto datetime ciente do fuso horário local
            agendamento_aware_dt = django_timezone.localize(agendamento_local_dt)

            # Converte para UTC antes de salvar no banco de dados (boa prática do Django)
            data_execucao_agendada_utc = agendamento_aware_dt.astimezone(pytz.utc)


            ComandoPendente.objects.create(
                dispositivo=dispositivo,
                comando=comando_texto,
                parametros=json.dumps(parametros_parsed),
                data_execucao_agendada=data_execucao_agendada_utc # Salva a data/hora agendada
            )
            messages.success(request, f"Comando '{comando_texto}' agendado para '{dispositivo.nome}' em {agendamento_aware_dt.strftime('%d/%m/%Y %H:%M')} com sucesso!")
        except json.JSONDecodeError:
            messages.error(request, "Erro: Parâmetros JSON inválidos. Certifique-se de que é um JSON válido, ex: {'temperatura': 22}.")
        except ValueError as e: # Captura erros de formatação de data/hora ou JSON
            messages.error(request, f"Erro ao processar dados: {e}. Verifique o formato da data/hora e do JSON.")
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao agendar o comando: {e}")

        return redirect('gerenciar_dispositivos')

    # Para requisições GET (exibição da página)
    # ... (seu código existente para GET) ...
    dispositivos = Dispositivo.objects.all().order_by('nome')
    leituras_recentes = {}
    for disp in dispositivos:
        leitura = LeituraSensor.objects.filter(dispositivo=disp).order_by('-timestamp').first()
        leituras_recentes[disp.id] = leitura

    comandos_pendentes_por_dispositivo = {}
    for disp in dispositivos:
        # AQUI: Ajustar para mostrar comandos que *ainda não foram executados*
        # e que a data agendada já passou ou é o momento atual
        comandos = ComandoPendente.objects.filter(dispositivo=disp, executado=False).order_by('data_execucao_agendada')
        comandos_pendentes_por_dispositivo[disp.id] = comandos

    context = {
        'dispositivos': dispositivos,
        'leituras_recentes': leituras_recentes,
        'comandos_pendentes': comandos_pendentes_por_dispositivo,
    }
    return render(request, 'iot_core/gerenciar_dispositivos.html', context)




