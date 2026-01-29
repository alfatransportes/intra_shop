# website/forms.py
from django import forms

from .models import FormaPagamento, Venda


class CheckoutForm(forms.Form):
    forma_pagamento = forms.ModelChoiceField(
        queryset=FormaPagamento.objects.filter(ativa=True),
        empty_label=None,
        widget=forms.RadioSelect,
        label="Forma de pagamento",
    )
    observacao = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class ComprovantePixForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = ["comprovante_pix"]

    def clean_comprovante_pix(self):
        f = self.cleaned_data.get("comprovante_pix")
        if not f:
            return f

        # opcional: limite 5MB
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Arquivo muito grande (máx. 5MB).")

        return f