# website/forms.py
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import FormaPagamento, RegraParcelamentoVale, Venda


class CheckoutForm(forms.Form):
    forma_pagamento = forms.ModelChoiceField(
        queryset=FormaPagamento.objects.filter(ativa=True),
        empty_label=None,
        widget=forms.RadioSelect,
        label="Forma de pagamento",
    )

    parcelas = forms.ChoiceField(
        choices=[("1", "1x")],
        required=False,
        label="Parcelamento",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        label="Observação",
    )

    def __init__(self, *args, total=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.total = Decimal(str(total or "0.00")).quantize(Decimal("0.01"))

        # classe bootstrap nos radios (opcional)
        self.fields["forma_pagamento"].widget.attrs.update({"class": "form-check-input"})

        # Descobre qual forma está selecionada (POST) ou inicial
        forma = None
        if self.is_bound:
            raw = (self.data.get("forma_pagamento") or "").strip()
            if raw.isdigit():
                forma = FormaPagamento.objects.filter(pk=int(raw), ativa=True).first()
        else:
            inicial = self.initial.get("forma_pagamento")
            if isinstance(inicial, FormaPagamento):
                forma = inicial
            elif isinstance(inicial, int):
                forma = FormaPagamento.objects.filter(pk=inicial, ativa=True).first()

        # ----------------------------------------------------
        # ✅ Monta as parcelas com base nas regras do VALE
        #    mesmo no GET, para o select já vir preenchido.
        # ----------------------------------------------------
        vale = FormaPagamento.objects.filter(
            codigo=FormaPagamento.Codigo.VALE,
            ativa=True
        ).first()

        max_parcelas = 1
        if vale:
            regra = (
                RegraParcelamentoVale.objects
                .filter(forma_pagamento=vale, valor_ate__gte=self.total)
                .order_by("valor_ate")
                .first()
            )
            if regra:
                max_parcelas = int(regra.max_parcelas or 1)

        self.fields["parcelas"].choices = [
            (str(i), f"{i}x") for i in range(1, max_parcelas + 1)
        ]

        # se não for VALE, mantém 1 como padrão
        if not (forma and forma.codigo == FormaPagamento.Codigo.VALE):
            self.fields["parcelas"].initial = "1"

        self.fields["parcelas"].required = False

    def clean(self):
        cleaned = super().clean()
        forma = cleaned.get("forma_pagamento")

        parcelas_raw = cleaned.get("parcelas") or "1"
        try:
            parcelas = int(parcelas_raw)
        except ValueError:
            parcelas = 1

        if not forma:
            return cleaned

        if forma.codigo == FormaPagamento.Codigo.VALE:
            regra = (
                RegraParcelamentoVale.objects
                .filter(forma_pagamento=forma, valor_ate__gte=self.total)
                .order_by("valor_ate")
                .first()
            )

            if not regra:
                raise ValidationError(
                    "Não existe regra de parcelamento cadastrada para este valor no VALE."
                )

            if parcelas < 1 or parcelas > int(regra.max_parcelas):
                raise ValidationError(
                    f"Parcelamento inválido. Para este total, o máximo é {regra.max_parcelas}x."
                )

            cleaned["parcelas"] = parcelas
        else:
            cleaned["parcelas"] = 1

        return cleaned

class ComprovantePixForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = ["comprovante_pix"]
        labels = {"comprovante_pix": "Comprovante do Pix"}
        help_texts = {"comprovante_pix": "Envie um comprovante em PDF, JPG ou PNG (máx. 5MB)."}
        widgets = {
            "comprovante_pix": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",          # Bootstrap
                    "accept": ".pdf,.jpg,.jpeg,.png", # ajuda no seletor
                }
            )
        }

    def clean_comprovante_pix(self):
        f = self.cleaned_data.get("comprovante_pix")
        if not f:
            raise ValidationError("Envie o comprovante do Pix para continuar.")

        # limite 5MB
        if f.size > 5 * 1024 * 1024:
            raise ValidationError("Arquivo muito grande (máx. 5MB).")

        # valida extensão (rápido e suficiente na maioria dos casos)
        nome = (f.name or "").lower()
        ext_ok = (".pdf", ".jpg", ".jpeg", ".png")
        if not nome.endswith(ext_ok):
            raise ValidationError("Formato inválido. Envie PDF, JPG ou PNG.")

        # valida content-type quando disponível (nem todo upload garante isso 100%)
        ct = (getattr(f, "content_type", "") or "").lower()
        ct_ok = {"application/pdf", "image/jpeg", "image/png"}
        if ct and ct not in ct_ok:
            raise ValidationError("Tipo de arquivo inválido. Envie PDF, JPG ou PNG.")

        return f
