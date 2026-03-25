# custom_tags.py

import re
from decimal import Decimal, InvalidOperation

from babel.numbers import format_currency
from django import template

register = template.Library()

@register.filter
def get_attr(obj, attr_name):
    return getattr(obj, attr_name, "")

@register.filter(name='format_telefone')
def format_telefone(value: str) -> str:
    if not value:
        return value

    numero = re.sub(r'\D', '', value)

    if len(numero) == 11:
        ddd = numero[:2]
        primeiro = numero[2:3]
        meio = numero[3:7]
        fim = numero[7:]
        return f"({ddd}) {primeiro} {meio}-{fim}"

    if len(numero) == 10:
        ddd = numero[:2]
        meio = numero[2:6]
        fim = numero[6:]
        return f"({ddd}) {meio}-{fim}"

    return value




@register.filter(name='format_cnpj')
def format_cnpj(value):
    if len(value) == 14:
        return f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:14]}"
    else:
        return value


@register.filter(name='raiz_cnpj')
def raiz_cnpj(value):
    if len(value) == 14:
        return f"{value[:2]}.{value[2:5]}.{value[5:8]}"
    else:
        return value


@register.filter(name='format_cpf')
def format_cpf(value):
    value = value[-11:]
    if len(value) == 11:
        return f"{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:11]}"
    else:
        return value


@register.filter(name='format_cep')
def format_cep(value):
    cep = str(value)
    if len(cep) == 8:
        return f"{cep[:2]}.{cep[2:5]}-{cep[5:8]}"
    else:
        return value


@register.filter(name='format_num_telefone')
def format_num_telefone(value):
    if len(value) == 10:
        return f"({value[:2]}) {value[2:6]}-{value[6:10]}"
    else:
        return value




@register.filter(name='currency_brl')
def currency_brl(value):
    # Nada ou nulo: não formata
    if value in (None, '', 'None'):
        return ''

    try:
        # Se vier como string, tenta normalizar
        if isinstance(value, str):
            # remove espaços
            value = value.strip()
            # se ainda estiver vazio depois do strip
            if value == '':
                return ''
            # se vier no formato brasileiro "1.234,56"
            # troca ponto de milhar e vírgula de decimal
            value = value.replace('.', '').replace(',', '.')

        # Garante que é Decimal ou algo numérico
        value = Decimal(str(value))

        return format_currency(value, 'BRL', locale='pt_BR')
    except (InvalidOperation, TypeError, ValueError):
        # Se der erro, devolve o valor "cru"
        return value
