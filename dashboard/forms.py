from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from website.models import (FormaPagamento, NivelAvaria, Produto,
                            ProdutoImagem, RegraParcelamentoVale, Tipo,
                            Unidade, Venda, VendaItem)


class BaseBootstrapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "form-control"
                widget.attrs.setdefault("rows", 4)
            elif isinstance(widget, forms.FileInput):
                existing_class = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{existing_class} form-control".strip()
            else:
                widget.attrs["class"] = "form-control"


class TipoForm(BaseBootstrapForm):
    class Meta:
        model = Tipo
        fields = ["nome", "ativo"]


class UnidadeForm(BaseBootstrapForm):
    class Meta:
        model = Unidade
        fields = ["codigo", "nome"]


class NivelAvariaForm(BaseBootstrapForm):
    class Meta:
        model = NivelAvaria
        fields = ["nome"]


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


class ProdutoForm(BaseBootstrapForm):
    class Meta:
        model = Produto
        fields = [
            "unidade_prod",
            "tipo_prod",
            "nivel_ava_prod",
            "num_controle",
            "nome",
            "quantidade",
            "maximo_por_usuario",
            "valor_nota",
            "porcen_desconto",
            "descricao",
            "ativo",
        ]

    def clean(self):
        cleaned_data = super().clean()
        ativo = cleaned_data.get("ativo")

        if ativo and not self.instance.pk:
            self.add_error(
                "ativo",
                "Para ativar o produto, salve primeiro e adicione ao menos uma imagem."
            )
            return cleaned_data

        if ativo and self.instance.pk and not self.instance.imagens.exists():
            self.add_error(
                "ativo",
                "Para ativar o produto, adicione ao menos uma imagem."
            )

        return cleaned_data


class ProdutoImportForm(forms.Form):
    arquivo = forms.FileField(
        label="Planilha",
        help_text="Formatos aceitos: CSV, XLS, XLSX",
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control"}
        ),
    )
    

class ProdutoImagemForm(BaseBootstrapForm):
    class Meta:
        model = ProdutoImagem
        fields = ["imagem", "legenda", "ordem", "principal"]
        widgets = {
            "imagem": forms.ClearableFileInput(attrs={
                "accept": "image/*",
                "class": "form-control",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        principal = cleaned_data.get("principal")
        imagem = cleaned_data.get("imagem")
        deletar = cleaned_data.get("DELETE")
        imagem_existente = bool(self.instance and self.instance.pk and self.instance.imagem)

        if deletar:
            return cleaned_data

        if principal and not imagem and not imagem_existente:
            self.add_error(
                "imagem",
                "Selecione uma imagem antes de marcar como principal."
            )

        return cleaned_data


class BaseProdutoImagemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        principais = 0
        imagens_validas = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            imagem = form.cleaned_data.get("imagem")
            imagem_existente = bool(form.instance and form.instance.pk and form.instance.imagem)

            if imagem or imagem_existente:
                imagens_validas += 1

            if form.cleaned_data.get("principal"):
                principais += 1

        if principais > 1:
            raise forms.ValidationError("Marque apenas uma imagem como principal.")

        if imagens_validas > 0 and principais == 0:
            raise forms.ValidationError("Selecione uma imagem principal.")


ProdutoImagemFormSet = inlineformset_factory(
    Produto,
    ProdutoImagem,
    form=ProdutoImagemForm,
    formset=BaseProdutoImagemFormSet,
    fields=["imagem", "legenda", "ordem", "principal"],
    extra=0,
    can_delete=True,
)


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


class VendaForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = [
            "usuario",
            "forma_pagamento",
            "status",
            "parcelas",
            "minuta",
            "comprovante_pix",
            "comprovante_vale",
            "observacao",
        ]
        widgets = {
            "observacao": forms.Textarea(attrs={"rows": 4}),
            "minuta": forms.TextInput(attrs={"placeholder": "Informe a minuta, se houver"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["forma_pagamento"].queryset = FormaPagamento.objects.filter(ativa=True)

        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "form-control"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "form-control"
            else:
                widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        forma = cleaned_data.get("forma_pagamento")
        comprovante_pix = cleaned_data.get("comprovante_pix")
        comprovante_vale = cleaned_data.get("comprovante_vale")
        minuta = cleaned_data.get("minuta")

        if minuta and status not in [Venda.Status.APROVADA, Venda.Status.CONCLUIDA]:
            self.add_error(
                "minuta",
                "A minuta só pode ser informada quando a venda estiver como APROVADA ou CONCLUIDA."
            )

        if forma:
            if forma.codigo == "PIX" and not comprovante_pix:
                self.add_error(
                    "comprovante_pix",
                    "Para vendas com pagamento via Pix, anexe o comprovante."
                )

            if forma.codigo == "VALE" and not comprovante_vale:
                self.add_error(
                    "comprovante_vale",
                    "Para vendas com pagamento via Vale, anexe o comprovante."
                )

        return cleaned_data


class ProdutoVendaSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        raw_value = getattr(value, "value", value)
        produto_id = None

        if raw_value not in (None, ""):
            try:
                produto_id = int(raw_value)
            except (TypeError, ValueError):
                produto_id = None

        if produto_id:
            produto = Produto.objects.filter(pk=produto_id).first()
            if produto:
                option["attrs"]["data-preco"] = str(produto.valor_venda)
                option["attrs"]["data-estoque"] = str(produto.estoque_disponivel)

        return option


class VendaItemForm(forms.ModelForm):
    subtotal_exibicao = forms.DecimalField(
        label="Subtotal",
        required=False,
        decimal_places=2,
        max_digits=12,
        disabled=True,
    )

    class Meta:
        model = VendaItem
        fields = ["produto", "quantidade", "preco_unitario"]
        widgets = {
            "quantidade": forms.NumberInput(attrs={"min": 1}),
            "preco_unitario": forms.NumberInput(attrs={"step": "0.01", "readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["produto"].queryset = Produto.objects.filter(ativo=True).order_by("nome")
        self.fields["produto"].widget.attrs["class"] = "form-select"
        self.fields["quantidade"].widget.attrs["class"] = "form-control"
        self.fields["preco_unitario"].widget.attrs["class"] = "form-control"
        self.fields["subtotal_exibicao"].widget.attrs["class"] = "form-control"

        produto = None
        quantidade = 1

        if self.is_bound:
            produto_id = self.data.get(self.add_prefix("produto"))
            if produto_id:
                produto = Produto.objects.filter(pk=produto_id).first()

            try:
                quantidade = int(self.data.get(self.add_prefix("quantidade")) or 1)
            except (TypeError, ValueError):
                quantidade = 1

        elif self.instance and self.instance.pk:
            produto = self.instance.produto
            quantidade = self.instance.quantidade or 1

        if produto:
            self.initial["preco_unitario"] = produto.valor_venda
            self.initial["subtotal_exibicao"] = (
                Decimal(produto.valor_venda) * Decimal(quantidade)
            ).quantize(Decimal("0.01"))
        elif self.instance and self.instance.pk:
            self.initial["preco_unitario"] = self.instance.preco_unitario
            self.initial["subtotal_exibicao"] = self.instance.subtotal

    def clean(self):
        cleaned_data = super().clean()

        produto = cleaned_data.get("produto")
        quantidade = cleaned_data.get("quantidade") or 0

        if not produto:
            if quantidade:
                self.add_error("produto", "Selecione um produto.")
            return cleaned_data

        if quantidade <= 0:
            self.add_error("quantidade", "Informe uma quantidade maior que zero.")
            return cleaned_data

        estoque_limite = produto.estoque_disponivel
        if self.instance and self.instance.pk and self.instance.produto_id == produto.id:
            estoque_limite += self.instance.quantidade or 0

        if quantidade > estoque_limite:
            self.add_error(
                "quantidade",
                f"Estoque disponível para este produto: {estoque_limite}."
            )

        cleaned_data["preco_unitario"] = produto.valor_venda
        cleaned_data["subtotal_exibicao"] = (
            Decimal(produto.valor_venda) * Decimal(quantidade)
        ).quantize(Decimal("0.01"))

        return cleaned_data


VendaItemFormSet = inlineformset_factory(
    Venda,
    VendaItem,
    form=VendaItemForm,
    extra=1,
    can_delete=True,
)

