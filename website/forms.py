# website/forms.py
from django import forms
from django.core.exceptions import ValidationError

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
