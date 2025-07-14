# iot_core/urls.py

from django.urls import path
from . import views # Importa as views da sua app

urlpatterns = [
    path('', views.home, name='home'), # Exemplo: uma página inicial para a app
    path('receber_dados_sensor/', views.receber_dados_sensor, name='receber_dados_sensor'), # recebe dados de temp
    path('comando/<str:device_name>/', views.enviar_comando_dispositivo, name='enviar_comando_dispositivo'), # enviar comandos (quando tiver)
    path('gerenciar/', views.gerenciar_dispositivos, name='gerenciar_dispositivos'), # gerenciar dispositivos e comandos
]

