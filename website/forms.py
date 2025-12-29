# website/forms.py
from django import forms

from .models import FormaPagamento


class CheckoutForm(forms.Form):
    forma_pagamento = forms.ModelChoiceField(
        queryset=FormaPagamento.objects.filter(ativa=True),
        empty_label=None,
        widget=forms.RadioSelect,
        label="Forma de pagamento",
    )
    observacao = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))