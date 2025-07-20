# MeuProjetoIoT_Django/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views # Importe as views de autenticação

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('iot_core.urls')), # Inclui as URLs da sua app iot_core

    # Adicione esta linha para a URL de logout
    # Você pode definir next_page para onde o usuário será redirecionado após o logout
    path('logout/', auth_views.LogoutView.as_view(next_page='/home'), name='logout'),

]
