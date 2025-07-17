// iot_esp8266_firmware.ino
#include <Arduino.h> 
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <DHT.h> // Instale esta biblioteca (DHT-sensor-library por adafruit.com/dht) via Gerenciador de Bibliotecas da IDE Arduino
#include <ArduinoJson.h> // Instale esta biblioteca via Gerenciador de Bibliotecas da IDE Arduino
#include <IRremoteESP8266.h> // Instale esta biblioteca via Gerenciador de Bibliotecas da IDE Arduino
#include <IRsend.h>         // Instale esta biblioteca via Gerenciador de Bibliotecas da IDE Arduino

//Pinagem do ESP8266 Pinos Digitais (GPIO):
#define D0 16
#define D1 5
#define D2 4
#define D3 0
#define D4 2
#define D5 14
#define D6 12
#define D7 13
#define D8 15 
//Pinagem do ESP8266 Outros Pinos:
// #define RX 3 // Recebe dados
// #define TX 1 //- Transmite dados
// #define A0 17 //ADC) - Pino analógico e entrada digital
// //VU - Vin (entrada de tensão, 5V, opcional)
// //3V3 - Saída de 3.3V
// //RST - Reset
// //EN (ou CH_PD) - Habilitação do chip (ativo em nível alto) 

// --- Configurações de Rede ---
const char* ssid = "IFSP-LAB";       // Seu nome de rede Wi-Fi
const char* password = "%mf*GP-10RpGm";  // Sua senha do Wi-Fi

// --- Configurações do Servidor Django ---
const char* djangoHost = "10.123.71.216"; // O IP do seu computador onde o Django está rodando (ex: 192.168.1.100)
const int djangoPort = 8000;              // A porta do Django (padrão 8000)
const char* deviceName = "Meu_ESP_Teste"; // O nome do dispositivo cadastrado no Django Admin


//comandoLigar
uint16_t rawData1[349] = {742, 17772,  3270, 8748,  740, 254,  756, 1240,  760, 238,  760, 240,  756, 240,  760, 240,  758, 238,  760, 236,  762, 242,  754, 1242,  756, 240,  756, 240,  758, 1268,  734, 264,  634, 366,  718, 1278,  740, 1258,  756, 1240,  750, 1248,  746, 1250,  746, 254,  732, 276,  720, 268,  726, 278,  712, 286,  698, 302,  668, 360,  634, 376,  620, 380,  588, 420,  572, 434,  562, 436,  558, 442,  550, 448,  544, 456,  536, 462,  530, 470,  520, 480,  512, 486,  506, 492,  500, 498,  496, 504,  494, 522,  476, 528,  470, 530,  470, 528,  484, 514,  494, 504,  494, 504,  494, 504,  496, 502,  492, 506,  490, 1506,  492, 1506,  496, 1500,  494, 1502,  498, 3014,  2978, 9010,  496, 1526,  470, 528,  468, 530,  490, 508,  494, 504,  498, 500,  498, 500,  494, 504,  498, 500,  498, 1498,  496, 502,  494, 504,  496, 1502,  494, 502,  494, 1504,  496, 1526,  470, 1528,  468, 1530,  494, 1504,  498, 1498,  496, 504,  498, 500,  494, 504,  494, 502,  496, 502,  494, 504,  496, 500,  494, 504,  496, 506,  496, 514,  480, 526,  472, 530,  466, 532,  470, 528,  494, 504,  498, 500,  498, 500,  496, 502,  496, 502,  494, 506,  498, 500,  500, 498,  498, 500,  496, 502,  498, 500,  498, 500,  500, 498,  498, 512,  484, 524,  474, 528,  472, 526,  472, 526,  494, 504,  496, 502,  500, 498,  498, 500,  496, 3010,  2982, 9010,  494, 1500,  498, 500,  500, 498,  496, 502,  496, 502,  496, 500,  498, 502,  496, 516,  478, 528,  472, 1530,  490, 506,  496, 504,  498, 1498,  496, 500,  496, 1502,  496, 1500,  496, 502,  494, 1502,  496, 1500,  498, 1500,  496, 1522,  474, 1528,  470, 528,  496, 1502,  496, 1500,  496, 502,  496, 502,  496, 502,  496, 1500,  496, 1500,  498, 1500,  496, 502,  496, 502,  496, 522,  476, 524,  474, 528,  470, 528,  488, 510,  496, 1502,  500, 496,  498, 1500,  496, 1502,  496, 500,  496, 1502,  496, 1500,  494, 502,  498, 500,  496, 504,  498, 514,  484, 524,  472, 530,  468, 530,  490, 1506,  500, 1498,  496, 1502,  496, 1500,  498};  // UNKNOWN B2D4D5E3
//comandoDesligar
uint16_t rawData2[349] = {830, 17684,  3268, 8748,  750, 246,  756, 1242,  758, 242,  756, 240,  758, 242,  758, 242,  756, 238,  760, 240,  758, 242,  754, 1244,  754, 240,  756, 240,  754, 1276,  712, 1282,  726, 270,  732, 1268,  754, 1242,  752, 1246,  750, 1248,  742, 1254,  736, 266,  730, 266,  728, 274,  718, 276,  720, 278,  690, 334,  646, 368,  632, 372,  622, 378,  584, 428,  566, 436,  558, 442,  550, 450,  542, 456,  534, 466,  526, 472,  518, 480,  514, 486,  504, 494,  500, 498,  494, 510,  488, 524,  472, 530,  470, 532,  470, 528,  488, 510,  492, 504,  492, 508,  494, 504,  494, 504,  492, 506,  494, 504,  496, 502,  496, 502,  492, 1506,  490, 1506,  494, 3014,  2982, 9006,  494, 1524,  472, 530,  472, 526,  492, 506,  494, 504,  500, 498,  496, 502,  496, 502,  498, 502,  496, 1502,  496, 502,  494, 502,  496, 1500,  496, 504,  494, 1510,  490, 1522,  474, 1526,  468, 1530,  496, 1502,  498, 1500,  496, 502,  496, 502,  498, 500,  494, 504,  494, 504,  494, 504,  496, 502,  498, 500,  496, 502,  496, 514,  484, 524,  474, 524,  474, 528,  470, 528,  496, 504,  496, 502,  498, 502,  496, 500,  498, 500,  496, 502,  498, 500,  498, 500,  500, 500,  498, 500,  496, 502,  494, 504,  496, 502,  496, 512,  488, 522,  472, 528,  470, 530,  468, 530,  496, 502,  496, 502,  496, 500,  498, 502,  498, 3004,  2986, 9006,  498, 1498,  498, 500,  498, 500,  496, 502,  494, 504,  494, 504,  496, 512,  488, 518,  474, 528,  474, 1526,  488, 510,  496, 502,  496, 1502,  496, 1502,  494, 1502,  496, 1502,  496, 502,  494, 1504,  496, 1500,  496, 1502,  496, 1522,  474, 1528,  468, 528,  494, 1502,  494, 1504,  496, 502,  494, 504,  494, 504,  496, 1502,  494, 1502,  496, 1500,  496, 500,  494, 506,  496, 518,  476, 528,  476, 524,  470, 528,  494, 504,  496, 1500,  498, 500,  496, 1502,  498, 1500,  494, 504,  498, 1500,  496, 1500,  496, 502,  496, 502,  498, 514,  480, 524,  476, 526,  474, 528,  470, 528,  494, 504,  494, 504,  498, 1500,  498, 1500,  496};  // UNKNOWN D5BA3FD0
//ComandoModoFAN
uint16_t rawData3[233] = {848, 17754,  3272, 8744,  728, 266,  750, 1248,  760, 238,  756, 240,  756, 246,  754, 240,  758, 242,  750, 246,  756, 240,  758, 1244,  752, 246,  752, 248,  748, 1282,  718, 282,  624, 368,  712, 1284,  736, 1258,  754, 1244,  746, 1252,  742, 1260,  730, 264,  732, 280,  714, 280,  712, 288,  708, 278,  704, 302,  668, 364,  628, 378,  616, 384,  586, 418,  576, 434,  562, 438,  556, 442,  550, 448,  544, 454,  536, 462,  530, 468,  520, 480,  514, 486,  504, 494,  500, 500,  496, 506,  492, 522,  476, 522,  470, 534,  466, 532,  464, 532,  492, 506,  494, 504,  492, 506,  494, 504,  494, 504,  494, 1504,  492, 1504,  492, 1504,  496, 1500,  496, 3014,  2978, 9016,  494, 1518,  474, 530,  468, 530,  486, 512,  496, 502,  496, 504,  496, 502,  496, 502,  496, 502,  492, 1506,  496, 502,  498, 502,  494, 1502,  494, 504,  496, 1508,  492, 1518,  476, 528,  470, 1528,  494, 1504,  498, 1498,  498, 1498,  496, 1502,  496, 502,  496, 1500,  500, 1498,  496, 502,  494, 504,  498, 518,  476, 1526,  472, 1528,  484, 1512,  498, 500,  494, 504,  496, 502,  494, 504,  496, 502,  498, 500,  496, 502,  494, 504,  494, 1502,  496, 1502,  500, 504,  492, 522,  474, 1530,  474, 1524,  492, 1506,  496, 502,  500, 500,  494, 502,  498, 500,  494, 504,  498, 500,  496, 1502,  496, 1502,  494, 1502,  496, 1520,  506};  // UNKNOWN 22580D61



// --- Configurações do DHT11 ---
#define DHTPIN D2     // Pino digital onde o DHT11 está conectado (GPIO4 no NodeMCU)
#define DHTTYPE DHT11 // Tipo de sensor (DHT11 ou DHT22)
DHT dht(DHTPIN, DHTTYPE);

// --- Configurações do IR ---
#define frequencia 38 // kHz
const int kIrLed = D1; // Pino do LED IR (GPIO5 no NodeMCU)
IRsend irsend(kIrLed); // Objeto para enviar sinais IR

// --- Configurações do Buzzer ---
const int buzzerPin = D3; // Pino do Buzzer (GPIO0 no NodeMCU)

// --- Configurações dos Botões ---
const int btnLigarPin = D5;    // Pino do botão Ligar (GPIO14)
const int btnDesligarPin = D6; // Pino do botão Desligar (GPIO12)
const int btnVentilacaoPin = D7; // Pino do botão Ventilação (GPIO13)

// --- Variáveis de Controle ---
unsigned long lastSendMillis = 0;
const long sendInterval = 30000; // Enviar dados a cada 30 segundos

// --- VARIÁVEL: para controlar o intervalo de verificação de comandos ---
unsigned long lastCommandCheckMillis = 0;
const long commandCheckInterval = 5000; // Verificar comandos a cada 5 segundos

void setup() {
  Serial.begin(115200);
  delay(10);

  // Inicializa o DHT
  dht.begin();

  // Inicializa o IR
  irsend.begin();

  // Configura os pinos dos botões como INPUT_PULLUP
  pinMode(btnLigarPin, INPUT_PULLUP);
  pinMode(btnDesligarPin, INPUT_PULLUP);
  pinMode(btnVentilacaoPin, INPUT_PULLUP);

  // Configura o pino do buzzer como OUTPUT
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW); // Garante que o buzzer esteja desligado no início

  Serial.print("Conectando-se a ");
  Serial.println(ssid);

  //WiFi.begin(ssid, password); // rede normal
  WiFi.begin(ssid, password, 0, NULL, true); //Rede da escola oculta

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado!");
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi Desconectado. Tentando reconectar...");
    WiFi.begin(ssid, password);
    // Não usar delay(5000) ou restart aqui. O loop continuará e tentará reconectar.
    // Você pode adicionar um pequeno delay para não ficar spamando a conexão
    delay(1000); 
    return; // Pula o resto do loop se não estiver conectado
  }

  // --- Leitura e Envio de Dados do Sensor para o Django ---
  if (millis() - lastSendMillis > sendInterval) {
    float h = dht.readHumidity();
    float t = dht.readTemperature(); // Lê temperatura em Celsius

    // Verifica se a leitura foi bem-sucedida
    if (isnan(h) || isnan(t)) {
      Serial.println("Falha ao ler do sensor DHT!");
    } else {
      Serial.print("Temperatura: ");
      Serial.print(t);
      Serial.print(" °C, Umidade: ");
      Serial.print(h);
      Serial.println(" %");

      sendSensorData(t, h); // Chama a função para enviar os dados
    }
    lastSendMillis = millis();
  }

   // --- Verificação de Comandos do Django ---
  if (millis() - lastCommandCheckMillis >= commandCheckInterval) {
      checkDjangoCommands();
      lastCommandCheckMillis = millis();
  }

  // --- Leitura dos Botões e Envio de Comandos IR ---
  if (digitalRead(btnLigarPin) == LOW) { // Botão Ligar pressionado
    delay(50); // Debounce
    if (digitalRead(btnLigarPin) == LOW) {
      Serial.println("Botão Ligar AR pressionado!");
      // Substitua rawDatax
      // Você precisará capturar esses códigos com um receptor IR
      irsend.sendRaw(rawData1, sizeof(rawData1) / sizeof(rawData1[0]), frequencia);// Comando raw Ligar
      tone(buzzerPin, 1000, 100); // Toca um bip curto
      while(digitalRead(btnLigarPin) == LOW); // Espera o botão ser solto
    }
  }


  if (digitalRead(btnDesligarPin) == LOW) { // Botão Desligar pressionado
    delay(50); // Debounce
    if (digitalRead(btnDesligarPin) == LOW) {
      Serial.println("Botão Desligar AR pressionado!");
      // Substitua rawDatax
      // Você precisará capturar esses códigos com um receptor IR
      irsend.sendRaw(rawData2, sizeof(rawData2) / sizeof(rawData2[0]), frequencia); //comando Desliga
      tone(buzzerPin, 1000, 100);
      while(digitalRead(btnDesligarPin) == LOW); // Espera o botão ser solto
    }
  }


  if (digitalRead(btnVentilacaoPin) == LOW) { // Botão Ventilação pressionado
    delay(50); // Debounce
    if (digitalRead(btnVentilacaoPin) == LOW) {
      Serial.println("Botão Ventilação AR pressionado!");
      // Substitua rawData1
      // Você precisará capturar esses códigos com um receptor IR
      irsend.sendRaw(rawData3, sizeof(rawData3) / sizeof(rawData3[0]), frequencia); //Comando Ventilação 
      tone(buzzerPin, 1000, 100);
      while(digitalRead(btnVentilacaoPin) == LOW); // Espera o botão ser solto
    }
  }


  delay(50); // Pequeno atraso para estabilidade
}

// --- Funções Auxiliares ---

void sendSensorData(float temperature, float humidity) {
  WiFiClient client;
  HTTPClient http;

  // Monta a URL completa para o endpoint de recebimento de dados
  String serverPath = "http://";
  serverPath += djangoHost;
  serverPath += ":";
  serverPath += djangoPort;
  serverPath += "/iot/receber_dados_sensor/";

  Serial.print("[HTTP] Enviando dados para: ");
  Serial.println(serverPath);

  http.begin(client, serverPath);
  http.addHeader("Content-Type", "application/json");

  // Cria o JSON para enviar
  StaticJsonDocument<200> doc; // Capacidade do JSON, ajuste se precisar de mais dados
  doc["dispositivo"] = deviceName;
  doc["temperatura"] = temperature;
  doc["umidade"] = humidity;

  String requestBody;
  serializeJson(doc, requestBody);

  Serial.print("[HTTP] Corpo da requisição: ");
  Serial.println(requestBody);

  int httpResponseCode = http.POST(requestBody);

  if (httpResponseCode > 0) {
    Serial.printf("[HTTP] Código de Resposta: %d\n", httpResponseCode);
    String response = http.getString();
    Serial.println(response);
  } else {
    Serial.printf("[HTTP] Erro na requisição: %s\n", http.errorToString(httpResponseCode).c_str());
  }
  http.end();
}

void checkDjangoCommands() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi não conectado, não foi possível verificar comandos.");
    return;
  }
  WiFiClient client;
  HTTPClient http;

  // Monta a URL completa para o endpoint de comando
  String serverPath = "http://";
  serverPath += djangoHost;
  serverPath += ":";
  serverPath += djangoPort;
  serverPath += "/iot/comando/";
  serverPath += deviceName;
  serverPath += "/"; 

  Serial.print("[HTTP] Verificando comandos em: ");
  Serial.println(serverPath);

  http.begin(client, serverPath);
  int httpResponseCode = http.GET();

  if (httpResponseCode > 0) {
    Serial.printf("[HTTP] Código de Resposta: %d\n", httpResponseCode);
    String response = http.getString();
    Serial.println(response);

    // Parseia a resposta JSON
    StaticJsonDocument<500> doc;
    DeserializationError error = deserializeJson(doc, response);

    if (error) {
      Serial.print(F("deserializeJson() falhou: "));
      Serial.println(error.c_str());
      return;
    }

   const char* status = doc["status"];
    const char* comandoRecebido = doc["comando"];
    int comando_id = doc["id_comando"] | 0; // Pega o ID do comando, 0 se não existir

    if (strcmp(status, "sucesso") == 0 && strcmp(comandoRecebido, "NENHUM_COMANDO") != 0) {
      Serial.print("Comando recebido do Django: ");
      Serial.println(comandoRecebido);

      // Você pode querer usar os parâmetros também
      // JsonObject parametros = doc["parametros"];
      // if (parametros.containsKey("temperatura")) {
      //   Serial.print("Temperatura nos parâmetros: ");
      //   Serial.println(parametros["temperatura"].as<int>());
      // }

      // --- Lógica para executar o comando recebido ---
      if (strcmp(comandoRecebido, "LIGAR_AR") == 0) {
        irsend.sendRaw(rawData1, sizeof(rawData1) / sizeof(rawData1[0]), frequencia);
        tone(buzzerPin, 1500, 200); // Bip de confirmação
        Serial.println("Comando LIGAR_AR executado.");
        enviarConfirmacaoComando(comando_id, "executado_sucesso");
      } else if (strcmp(comandoRecebido, "DESLIGAR_AR") == 0) {
        irsend.sendRaw(rawData2, sizeof(rawData2) / sizeof(rawData2[0]), frequencia);
        tone(buzzerPin, 1500, 200);
        Serial.println("Comando DESLIGAR_AR executado.");
        enviarConfirmacaoComando(comando_id, "executado_sucesso");
      } else if (strcmp(comandoRecebido, "VENTILACAO_AR") == 0) {
        irsend.sendRaw(rawData3, sizeof(rawData3) / sizeof(rawData3[0]), frequencia);
        tone(buzzerPin, 1500, 200);
        Serial.println("Comando VENTILACAO_AR executado.");
        enviarConfirmacaoComando(comando_id, "executado_sucesso");
      } else if (strcmp(comandoRecebido, "BUZZER_ON") == 0) {
        digitalWrite(buzzerPin, HIGH);
        Serial.println("Buzzer Ligado.");
        enviarConfirmacaoComando(comando_id, "executado_sucesso");
      } else if (strcmp(comandoRecebido, "BUZZER_OFF") == 0) {
        digitalWrite(buzzerPin, LOW);
        Serial.println("Buzzer Desligado.");
        enviarConfirmacaoComando(comando_id, "executado_sucesso");
      } else {
            Serial.print("Comando desconhecido: ");
            Serial.println(comandoRecebido);
            if (comando_id != 0) { // Se o comando não foi reconhecido, mas tinha ID, reporta falha
                enviarConfirmacaoComando(comando_id, "executado_falha_comando_desconhecido");
            }
        }
    } else if (strcmp(comandoRecebido, "NENHUM_COMANDO") == 0) {
        Serial.println("Nenhum comando pendente no Django.");
    } else {
        Serial.print("Status inesperado do Django: ");
        Serial.println(status);
    }
  } else {
    Serial.printf("[HTTP] Erro na requisição de comando: %s\n", http.errorToString(httpResponseCode).c_str());
  }
  http.end();
}

// Função para enviar confirmação de comando para o Django
void enviarConfirmacaoComando(int comandoId, const char* statusMsg) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi não conectado para enviar confirmação.");
    return;
  }
  WiFiClient client;
  HTTPClient http;

  String url = "http://" + String(djangoHost) + ":" + String(djangoPort) + "/iot/comando/" + String(deviceName) + "/";
  Serial.print("[HTTP] Enviando confirmação para: ");
  Serial.println(url);

  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<200> doc; // Capacidade do JSON, ajuste se necessário
  doc["comando_id"] = comandoId;
  doc["status"] = statusMsg;

  String requestBody;
  serializeJson(doc, requestBody);

  Serial.print("[HTTP] Corpo da requisição: ");
  Serial.println(requestBody);

  int httpResponseCode = http.POST(requestBody);

  if (httpResponseCode > 0) {
    Serial.printf("[HTTP] Código de Resposta de confirmação: %d\n", httpResponseCode);
    String payload = http.getString();
    Serial.println(payload);
  } else {
    Serial.printf("[HTTP] Erro ao enviar confirmação: %s\n", http.errorToString(httpResponseCode).c_str());
  }
  http.end();
}
