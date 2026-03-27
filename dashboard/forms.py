from django import forms

from website.models import (FormaPagamento, NivelAvaria, Produto,
                            ProdutoImagem, RegraParcelamentoVale, Tipo,
                            Unidade, Venda)


class BaseBootstrapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "form-control"
            else:
                widget.attrs["class"] = "form-control"


class TipoForm(BaseBootstrapForm):
    class Meta:
        model = Tipo
        fields = ["nome", "ativo"]


class UnidadeForm(BaseBootstrapForm):
    class Meta:
        model = Unidade
        fields = ["codigo","nome"]


class NivelAvariaForm(BaseBootstrapForm):
    class Meta:
        model = NivelAvaria
        fields = ["nome"]


# class VendaStatusForm(BaseBootstrapForm):
#     class Meta:
#         model = Venda
#         fields = ["status", "observacao", "comprovante_pix", "comprovante_vale"]

class VendaStatusForm(forms.ModelForm):

    class Meta:
        model = Venda
        fields = ["status", "comprovante_pix", "comprovante_vale", "minuta", "observacao"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        venda = self.instance

        if venda and venda.forma_pagamento.codigo == "PIX":
            self.fields.pop("comprovante_vale", None)

        if venda and venda.forma_pagamento.codigo == "VALE":
            self.fields.pop("comprovante_pix", None)

    def clean(self):
        cleaned_data = super().clean()

        status = cleaned_data.get("status")
        minuta = (cleaned_data.get("minuta") or "").strip()
        venda = self.instance
        forma = venda.forma_pagamento if venda else None

        if not venda or not forma:
            return cleaned_data

        comprovante_pix = cleaned_data.get("comprovante_pix") or venda.comprovante_pix
        comprovante_vale = cleaned_data.get("comprovante_vale") or venda.comprovante_vale

        if forma.codigo == "PIX" and status == Venda.Status.APROVADA and not comprovante_pix:
            self.add_error(
                "comprovante_pix",
                "Para aprovar uma venda Pix, o comprador deve anexar o comprovante primeiro."
            )

        if forma.codigo == "VALE" and status == Venda.Status.APROVADA and not comprovante_vale:
            self.add_error(
                "comprovante_vale",
                "Para aprovar uma venda em vale, anexe o comprovante primeiro."
            )

        if minuta and status not in [Venda.Status.APROVADA, Venda.Status.CONCLUIDA]:
            self.add_error(
                "minuta",
                "A minuta só pode ser informada quando a venda estiver com status Aprovada ou Concluída."
            )

        return cleaned_data

class FormaPagamentoForm(BaseBootstrapForm):
    class Meta:
        model = FormaPagamento
        fields = [
            "codigo",
            "ativa",
            "pix_chave",
            "pix_nome",
            "pix_cidade",
            "pix_payload",
        ]

    def clean(self):
        cleaned_data = super().clean()
        codigo = cleaned_data.get("codigo")

        if codigo == "PIX":
            if not cleaned_data.get("pix_chave"):
                self.add_error("pix_chave", "Informe a chave Pix.")
            if not cleaned_data.get("pix_nome"):
                self.add_error("pix_nome", "Informe o nome do recebedor do Pix.")
            if not cleaned_data.get("pix_cidade"):
                self.add_error("pix_cidade", "Informe a cidade do recebedor do Pix.")

        return cleaned_data


class RegraParcelamentoValeForm(BaseBootstrapForm):
    class Meta:
        model = RegraParcelamentoVale
        fields = ["minimo", "maximo", "max_parcelas", "ativo"]


        from django import forms

from django.forms import inlineformset_factory

from website.models import Produto, ProdutoImagem


class BaseBootstrapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "form-control"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "form-control"
                widget.attrs.setdefault("rows", 4)
            else:
                widget.attrs["class"] = "form-control"


class ProdutoForm(BaseBootstrapForm):
    class Meta:
        model = Produto
        fields = [
            "unidade_prod",
            "tipo_prod",
            "nivel_ava_prod",
            "nome",
            "quantidade",
            "maximo_por_usuario",
            "valor_nota",
            "porcen_desconto",
            "descricao",
        ]


class ProdutoImagemForm(BaseBootstrapForm):
    class Meta:
        model = ProdutoImagem
        fields = ["imagem", "legenda", "ordem", "principal"]
        widgets = {
            "imagem": forms.ClearableFileInput(attrs={
                "accept": "image/*",
                "capture": "environment",
                "class": "form-control",
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        principal = cleaned_data.get("principal")
        imagem = cleaned_data.get("imagem")

        if principal and not imagem and not self.instance.pk:
            raise forms.ValidationError("Selecione uma imagem antes de marcar como principal.")

        return cleaned_data


ProdutoImagemFormSet = inlineformset_factory(
    Produto,
    ProdutoImagem,
    form=ProdutoImagemForm,
    fields=["imagem", "legenda", "ordem", "principal"],
    extra=1,
    can_delete=True,
)