from django.apps import AppConfig


class IotCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'iot_core'

    def ready(self):
        # Importa seus filtros de template para que o Django os descubra
        import iot_core.templatetags.iot_filters 


