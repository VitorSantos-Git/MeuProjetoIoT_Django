# iot_core/templatetags/iot_filters.py

from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='split_and_map_weekday_names')
def split_and_map_weekday_names(value):
    if not value:
        return []
    
    weekday_map = {
        '0': 'Seg', '1': 'Ter', '2': 'Qua', '3': 'Qui',
        '4': 'Sex', '5': 'Sáb', '6': 'Dom'
    }
    
    days_numbers = [d.strip() for d in value.split(',') if d.strip().isdigit()]
    return [weekday_map.get(day_num, '') for day_num in days_numbers if weekday_map.get(day_num)]