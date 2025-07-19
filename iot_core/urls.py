# iot_core/urls.py

from django.urls import path
from . import views # Importa as views da sua app

urlpatterns = [
    path('', views.home, name='home'), # Exemplo: uma página inicial para a app
    path('receber_dados_sensor/', views.receive_sensor_data, name='receive_sensor_data'),  # recebe dados de temp
    path('comando/<str:device_name>/', views.enviar_comando_dispositivo, name='enviar_comando_dispositivo'), # enviar comandos (quando tiver)
    path('gerenciar/', views.gerenciar_dispositivos, name='gerenciar_dispositivos'), # Para acesso sem nome de dispositivo
    path('gerenciar/<str:device_name>/', views.gerenciar_dispositivos, name='gerenciar_dispositivos_com_nome'), # Para acesso com nome de dispositivo
    path('dashboard/', views.device_dashboard, name='device_dashboard'),
    path('add-device/', views.add_device, name='add_device'),
    path('delete-device/<int:device_id>/', views.delete_device, name='delete_device'),
    path('send-command/', views.send_command, name='send_command'),
    path('comando/<str:device_name>/', views.get_device_command, name='get_device_command'),
    path('comando/<str:device_name>/get/', views.get_device_command, name='get_device_command'),
    path('comando/<str:device_name>/send/', views.enviar_comando_dispositivo, name='enviar_comando_dispositivo'),
    path('atualizar_status_comando/', views.update_command_status, name='update_command_status'),
]

