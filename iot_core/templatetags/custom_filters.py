#iot_core\templatetags\custom_filters.py

from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Retorna o valor de um dicionário dado uma chave.
    Útil para acessar dicionários em templates Django.
    """
    return dictionary.get(key)