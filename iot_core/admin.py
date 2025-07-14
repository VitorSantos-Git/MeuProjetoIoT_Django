# iot_core/admin.py

from django.contrib import admin
from .models import Dispositivo, LeituraSensor, ComandoPendente  # Importe o seu modelo Dispositivo

# Registra o modelo Dispositivo no painel de administração
admin.site.register(Dispositivo)
admin.site.register(LeituraSensor)
admin.site.register(ComandoPendente)