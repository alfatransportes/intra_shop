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


class ProdutoForm(BaseBootstrapForm):
    class Meta:
        model = Produto
        fields = [
            "numero_bo",
            "unidade_prod",
            "tipo_prod",
            "nivel_ava_prod",
            "nome",
            "quantidade",
            "valor_nota",
            "porcen_desconto",
            "descricao",
        ]


class TipoForm(BaseBootstrapForm):
    class Meta:
        model = Tipo
        fields = ["nome", "ativo"]


class UnidadeForm(BaseBootstrapForm):
    class Meta:
        model = Unidade
        fields = ["nome"]


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
        fields = ["status", "observacao", "comprovante_pix", "comprovante_vale"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        venda = self.instance

        if venda.forma_pagamento.codigo == "PIX":
            self.fields.pop("comprovante_vale", None)

        if venda.forma_pagamento.codigo == "VALE":
            self.fields.pop("comprovante_pix", None)

class ProdutoImagemForm(BaseBootstrapForm):
    class Meta:
        model = ProdutoImagem
        fields = ["produto", "imagem", "legenda", "ordem", "principal"]

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get("produto")
        principal = cleaned_data.get("principal")

        if produto and principal:
            qs = ProdutoImagem.objects.filter(produto=produto, principal=True)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "principal",
                    "Já existe uma imagem principal para este produto."
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