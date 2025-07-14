# iot_core/urls.py

from django.urls import path
from . import views # Importa as views da sua app

urlpatterns = [
    path('', views.home, name='home'), # Exemplo: uma página inicial para a app
    path('receber_dados_sensor/', views.receber_dados_sensor, name='receber_dados_sensor'), # recebe dados de temp
    path('comando/<str:device_name>/', views.enviar_comando_dispositivo, name='enviar_comando_dispositivo'), # enviar comandos (quando tiver)
    # path('controle_led/', views.controle_led, name='controle_led'), # Exemplo: URL para controlar um LED
    # path('dados_sensor/', views.dados_sensor, name='dados_sensor'), # Exemplo: URL para receber dados de sensor
]

