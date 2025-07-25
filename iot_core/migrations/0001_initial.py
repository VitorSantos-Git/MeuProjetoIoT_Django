# Generated by Django 5.2.4 on 2025-07-13 22:43

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Dispositivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text="Nome único para identificar o dispositivo (ex: 'ESP8266_Sala').", max_length=100, unique=True)),
                ('descricao', models.TextField(blank=True, help_text='Descrição opcional do dispositivo e sua localização.', null=True)),
                ('ip_endereco', models.GenericIPAddressField(help_text='Endereço IP do dispositivo na rede local.', unique=True)),
                ('porta', models.IntegerField(default=80, help_text='Porta HTTP que o dispositivo está escutando (geralmente 80).')),
                ('ativo', models.BooleanField(default=True, help_text='Indica se o dispositivo está ativo e online.')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('ultima_atualizacao', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Dispositivo IoT',
                'verbose_name_plural': 'Dispositivos IoT',
                'ordering': ['nome'],
            },
        ),
    ]
