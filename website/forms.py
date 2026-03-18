# website/forms.py
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import (FormaPagamento, RegraParcelamentoVale,
                     validar_comprovante_pix)


class CheckoutForm(forms.Form):
    forma_pagamento = forms.ModelChoiceField(
        queryset=FormaPagamento.objects.filter(ativa=True),
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
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Observação",
    )

    def __init__(self, *args, total: Decimal = Decimal("0.00"), **kwargs):
        super().__init__(*args, **kwargs)
        self.total = (total or Decimal("0.00")).quantize(Decimal("0.01"))

        # Monta opções de parcelas do VALE conforme regra cadastrada
        try:
            vale = FormaPagamento.objects.get(codigo=FormaPagamento.Codigo.VALE, ativa=True)
        except FormaPagamento.DoesNotExist:
            vale = None

        max_parcelas = 1

        if vale:
            # Encontra a regra ativa que se encaixa no valor total:
            # minimo <= total AND (maximo is null OR total <= maximo)
            regras = (
                RegraParcelamentoVale.objects
                .filter(ativo=True, minimo__lte=self.total)
                .order_by("-minimo")
            )

            regra_escolhida = None
            for r in regras:
                if r.maximo is None or self.total <= r.maximo:
                    regra_escolhida = r
                    break

            if regra_escolhida:
                max_parcelas = max(1, int(regra_escolhida.max_parcelas or 1))

        # Atualiza choices do campo parcelas
        self.fields["parcelas"].choices = [(str(i), f"{i}x") for i in range(1, max_parcelas + 1)]

    def clean(self):
        cleaned = super().clean()
        forma = cleaned.get("forma_pagamento")
        parcelas = cleaned.get("parcelas")

        # Se escolheu VALE, parcelas é obrigatório e deve estar dentro das choices
        if forma and forma.codigo == FormaPagamento.Codigo.VALE:
            if not parcelas:
                raise ValidationError("Selecione a quantidade de parcelas para Vale.")
            # valida se está nas opções (Django já valida, mas deixo explícito)
            valid_values = {v for v, _lbl in self.fields["parcelas"].choices}
            if str(parcelas) not in valid_values:
                raise ValidationError("Parcelas inválidas para o valor desta compra.")

        return cleaned


class ComprovantePixForm(forms.Form):
    comprovante_pix = forms.FileField(
        required=True,
        label="Comprovante Pix (PNG/JPG/PDF)",
    )

    def clean_comprovante_pix(self):
        arquivo = self.cleaned_data.get("comprovante_pix")
        validar_comprovante_pix(arquivo)
        return arquivo