from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import (FormaPagamento, RegraParcelamentoVale,
                     validar_comprovante_pix)


class CheckoutForm(forms.Form):
    forma_pagamento = forms.ModelChoiceField(
        queryset=FormaPagamento.objects.filter(ativa=True).order_by("codigo"),
        empty_label=None,
        label="Forma de pagamento",
        required=True,
    )
    parcelas = forms.ChoiceField(
        choices=[("1", "1x")],
        required=False,
        label="Parcelas (Vale)",
    )
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Observação opcional do pedido"}),
        required=False,
        label="Observação",
    )

    def __init__(self, *args, total: Decimal = Decimal("0.00"), **kwargs):
        super().__init__(*args, **kwargs)
        self.total = (total or Decimal("0.00")).quantize(Decimal("0.01"))
        self._configurar_parcelas_vale()

    def _configurar_parcelas_vale(self):
        max_parcelas = 1
        regras = (
            RegraParcelamentoVale.objects.filter(ativo=True, minimo__lte=self.total)
            .order_by("-minimo")
        )
        for regra in regras:
            if regra.maximo is None or self.total <= regra.maximo:
                max_parcelas = max(1, int(regra.max_parcelas or 1))
                break
        self.fields["parcelas"].choices = [(str(i), f"{i}x") for i in range(1, max_parcelas + 1)]

    def clean(self):
        cleaned = super().clean()
        forma = cleaned.get("forma_pagamento")
        parcelas = str(cleaned.get("parcelas") or "")
        if forma and forma.codigo == FormaPagamento.Codigo.VALE:
            if not parcelas:
                raise ValidationError("Selecione a quantidade de parcelas para Vale.")
            valid_values = {valor for valor, _ in self.fields["parcelas"].choices}
            if parcelas not in valid_values:
                raise ValidationError("Parcelas inválidas para o valor desta compra.")
        else:
            cleaned["parcelas"] = "1"
        return cleaned


class ComprovantePixForm(forms.Form):
    comprovante_pix = forms.FileField(required=True, label="Comprovante Pix (PNG/JPG/PDF)")

    def clean_comprovante_pix(self):
        arquivo = self.cleaned_data.get("comprovante_pix")
        validar_comprovante_pix(arquivo)
        return arquivo
