# iot_core/views.py

from django.shortcuts import render, get_object_or_404, redirect # Importe get_object_or_404
from django.http import HttpResponse, JsonResponse # Importe JsonResponse
from django.views.decorators.csrf import csrf_exempt # Para desabilitar o CSRF temporariamente para a API
import json # Para lidar com JSON
from .models import Dispositivo, LeituraSensor, ComandoPendente # Importe o novo modelo LeituraSensor
from django.utils import timezone # Importe timezone para timestamps
from django.contrib import messages # Importe messages para feedback ao usuário

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
    # O ESP8266 faz um GET para esta URL para ver se há comandos pendentes
    # Busca o dispositivo pelo nome, ou retorna 404 se não encontrado
    dispositivo = get_object_or_404(Dispositivo, nome=device_name)

    # Procura por um comando pendente (executado=False) para este dispositivo
    comando_pendente = ComandoPendente.objects.filter(
        dispositivo=dispositivo,
        executado=False
    ).order_by('data_criacao').first() # Pega o comando mais antigo (primeiro na fila)

    if comando_pendente:
        # Encontrou um comando pendente, envia para o ESP e o marca como executado
        comando_para_enviar = {
            "status": "sucesso",
            "comando": comando_pendente.comando,
            "parametros": json.loads(comando_pendente.parametros) if comando_pendente.parametros else {},
            "dispositivo": dispositivo.nome
        }
        print(f"Enviando comando '{comando_pendente.comando}' para o dispositivo '{dispositivo.nome}'")

        # Marca o comando como executado no banco de dados
        comando_pendente.executado = True
        comando_pendente.data_execucao = timezone.now()
        comando_pendente.save()

        return JsonResponse(comando_para_enviar, status=200)
    else:
        # Não há comandos pendentes para este dispositivo
        print(f"Nenhum comando pendente para o dispositivo '{dispositivo.nome}'.")
        return JsonResponse({"status": "sucesso", "comando": "NENHUM_COMANDO", "dispositivo": dispositivo.nome}, status=200)
    

def gerenciar_dispositivos(request):
    # Esta view vai lidar tanto com a exibição quanto com o envio de comandos
    if request.method == 'POST':
        device_id = request.POST.get('device_id')
        comando_texto = request.POST.get('comando')
        parametros_json = request.POST.get('parametros', '{}') # Pega parâmetros, default para JSON vazio

        if not parametros_json:
            parametros_json = '{}'

        dispositivo = get_object_or_404(Dispositivo, id=device_id)

        try:
            # Tenta analisar os parâmetros como JSON
            parametros_parsed = json.loads(parametros_json)
            # Verifica se é um dicionário para garantir que pode ser salvo como JSON
            if not isinstance(parametros_parsed, dict):
                raise ValueError("Parâmetros devem ser um JSON válido (objeto).")

            ComandoPendente.objects.create(
                dispositivo=dispositivo,
                comando=comando_texto,
                parametros=json.dumps(parametros_parsed) # Salva como string JSON
            )
            messages.success(request, f"Comando '{comando_texto}' agendado para '{dispositivo.nome}' com sucesso!")
        except json.JSONDecodeError:
            messages.error(request, "Erro: Parâmetros JSON inválidos.")
        except ValueError as e:
            messages.error(request, f"Erro: {e}")
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao agendar o comando: {e}")

        return redirect('gerenciar_dispositivos') # Redireciona para evitar reenvio do formulário

    # Para requisições GET (exibição da página)
    dispositivos = Dispositivo.objects.all().order_by('nome')
    leituras_recentes = {}
    for disp in dispositivos:
        # Pega a leitura mais recente de cada dispositivo
        leitura = LeituraSensor.objects.filter(dispositivo=disp).order_by('-timestamp').first()
        leituras_recentes[disp.id] = leitura

    comandos_pendentes_por_dispositivo = {}
    for disp in dispositivos:
        # Pega os comandos pendentes de cada dispositivo
        comandos = ComandoPendente.objects.filter(dispositivo=disp, executado=False).order_by('data_criacao')
        comandos_pendentes_por_dispositivo[disp.id] = comandos


    context = {
        'dispositivos': dispositivos,
        'leituras_recentes': leituras_recentes,
        'comandos_pendentes': comandos_pendentes_por_dispositivo,
    }
    return render(request, 'iot_core/gerenciar_dispositivos.html', context)

