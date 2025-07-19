from django import forms
from .models import Dispositivo # Importa o seu modelo Dispositivo

class DispositivoForm(forms.ModelForm): # Nome do formulário para adicionar dispositivos
    class Meta:
        model = Dispositivo
        fields = ['nome', 'descricao', 'ip_endereco', 'porta', 'ativo'] # Use os campos do seu modelo Dispositivo
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do Dispositivo (Ex: Ar Sala)'}),
            'descricao': forms.Textarea(attrs={'placeholder': 'Descrição (opcional)', 'rows': 3}),
            'ip_endereco': forms.TextInput(attrs={'placeholder': 'Endereço IP (Ex: 192.168.1.100)'}),
            'porta': forms.NumberInput(attrs={'placeholder': 'Porta (Ex: 80)'}),
        }