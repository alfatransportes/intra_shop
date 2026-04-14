from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from website.models import (FormaPagamento, NivelAvaria, Produto,
                            ProdutoImagem, ProdutoVariacao,
                            RegraParcelamentoVale, Tipo, Unidade, Venda,
                            VendaItem)


class BaseBootstrapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                existing_class = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{existing_class} form-select".strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "form-control"
                widget.attrs.setdefault("rows", 4)
            elif isinstance(widget, forms.FileInput):
                existing_class = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{existing_class} form-control".strip()
            else:
                existing_class = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{existing_class} form-control".strip()


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
            "usa_variacoes",
            "quantidade",
            "maximo_por_usuario",
            "valor_nota",
            "porcen_desconto",
            "descricao",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantidade"].required = False
        self.fields["quantidade"].widget.attrs.setdefault("min", 0)

    def clean(self):
        cleaned_data = super().clean()
        ativo = cleaned_data.get("ativo")
        usa_variacoes = bool(cleaned_data.get("usa_variacoes"))
        quantidade = cleaned_data.get("quantidade")

        if usa_variacoes:
            cleaned_data["quantidade"] = 0
        elif quantidade in (None, ""):
            cleaned_data["quantidade"] = 0

        if ativo and not self.instance.pk:
            self.add_error(
                "ativo",
                "Para ativar o produto, salve primeiro e conclua as etapas obrigatórias."
            )
            return cleaned_data

        if ativo and self.instance.pk:
            self.instance.usa_variacoes = usa_variacoes
            self.instance.quantidade = int(cleaned_data.get("quantidade") or 0)
            pode_ativar, mensagem = self.instance.pode_ativar()
            if not pode_ativar:
                self.add_error("ativo", mensagem)

        if not usa_variacoes and int(cleaned_data.get("quantidade") or 0) <= 0:
            self.add_error(
                "quantidade",
                "Informe um estoque maior que zero para produto sem variações."
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


class ProdutoVariacaoForm(BaseBootstrapForm):
    class Meta:
        model = ProdutoVariacao
        fields = [
            "categoria",
            "genero",
            "faixa_etaria",
            "tamanho",
            "cor",
            "quantidade",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        categoria = None

        if self.is_bound:
            categoria = self.data.get(self.add_prefix("categoria"))
        elif self.instance and self.instance.pk:
            categoria = self.instance.categoria
        else:
            categoria = self.initial.get("categoria")

        if categoria == ProdutoVariacao.Categoria.PNEU:
            self.fields["tamanho"].label = "Medida"
            self.fields["tamanho"].help_text = "Ex.: 175/70R13, 205/55R16"
        else:
            self.fields["tamanho"].label = "Tamanho"
            self.fields["tamanho"].help_text = ""


class BaseProdutoVariacaoFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        combinacoes = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            categoria = form.cleaned_data.get("categoria")
            genero = form.cleaned_data.get("genero")
            faixa = form.cleaned_data.get("faixa_etaria")
            tamanho = (form.cleaned_data.get("tamanho") or "").strip().upper()
            cor = (form.cleaned_data.get("cor") or "").strip().lower()

            chave = (categoria, genero, faixa, tamanho, cor)

            if chave in combinacoes:
                raise forms.ValidationError(
                    "Já existe uma variação com esta combinação."
                )

            combinacoes.add(chave)

ProdutoVariacaoFormSet = inlineformset_factory(
    Produto,
    ProdutoVariacao,
    form=ProdutoVariacaoForm,
    formset=BaseProdutoVariacaoFormSet,
    fields=[
        "categoria",
        "genero",
        "faixa_etaria",
        "tamanho",
        "quantidade",
        "ativo",
    ],
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


class VendaForm(BaseBootstrapForm):
    class Meta:
        model = Venda
        fields = [
            "usuario",
            "forma_pagamento",
            "status",
            "parcelas",
            "observacao",
            "minuta",
            "comprovante_pix",
            "comprovante_vale",
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


class VendaItemForm(BaseBootstrapForm):
    variacao = forms.ModelChoiceField(
        queryset=ProdutoVariacao.objects.select_related("produto").filter(ativo=True),
        required=False,
        label="Variação",
    )

    subtotal_exibicao = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=12,
        label="Subtotal",
        widget=forms.NumberInput(attrs={"step": "0.01", "readonly": "readonly"}),
    )

    class Meta:
        model = VendaItem
        fields = [
            "produto",
            "variacao",
            "quantidade",
            "preco_unitario",
        ]
        widgets = {
            "preco_unitario": forms.NumberInput(attrs={"step": "0.01", "readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["produto"].queryset = Produto.objects.filter(ativo=True).order_by("nome")
        self.fields["produto"].widget.attrs["class"] = "form-select"
        self.fields["variacao"].widget.attrs["class"] = "form-select"
        self.fields["quantidade"].widget.attrs["class"] = "form-control"
        self.fields["preco_unitario"].widget.attrs["class"] = "form-control"
        self.fields["subtotal_exibicao"].widget.attrs["class"] = "form-control"

        produto = None
        variacao = None
        quantidade = 1

        if self.is_bound:
            produto_id = self.data.get(self.add_prefix("produto"))
            variacao_id = self.data.get(self.add_prefix("variacao"))

            if produto_id:
                produto = Produto.objects.filter(pk=produto_id).first()

            if variacao_id:
                variacao = ProdutoVariacao.objects.select_related("produto").filter(pk=variacao_id).first()

            try:
                quantidade = int(self.data.get(self.add_prefix("quantidade")) or 1)
            except (TypeError, ValueError):
                quantidade = 1

        elif self.instance and self.instance.pk:
            produto = self.instance.produto
            variacao = self.instance.variacao
            quantidade = self.instance.quantidade or 1

        if produto:
            self.fields["variacao"].queryset = ProdutoVariacao.objects.filter(
                produto=produto,
                ativo=True,
            ).order_by("categoria", "genero", "faixa_etaria", "tamanho", "cor", "id")

            self.initial["preco_unitario"] = produto.valor_venda
            self.initial["subtotal_exibicao"] = (
                Decimal(produto.valor_venda) * Decimal(quantidade)
            ).quantize(Decimal("0.01"))
        elif self.instance and self.instance.pk:
            self.initial["preco_unitario"] = self.instance.preco_unitario
            self.initial["subtotal_exibicao"] = self.instance.subtotal

        if variacao and not produto:
            produto = variacao.produto
            self.fields["variacao"].queryset = ProdutoVariacao.objects.filter(
                produto=produto,
                ativo=True,
            ).order_by("categoria", "genero", "faixa_etaria", "tamanho", "cor", "id")

    def clean(self):
        cleaned_data = super().clean()

        produto = cleaned_data.get("produto")
        variacao = cleaned_data.get("variacao")
        quantidade = cleaned_data.get("quantidade") or 0

        if not produto:
            if quantidade:
                self.add_error("produto", "Selecione um produto.")
            return cleaned_data

        if quantidade <= 0:
            self.add_error("quantidade", "Informe uma quantidade maior que zero.")
            return cleaned_data

        if produto.usa_variacoes:
            if not variacao:
                self.add_error("variacao", "Selecione uma variação para este produto.")
                return cleaned_data

            if variacao.produto_id != produto.id:
                self.add_error("variacao", "A variação selecionada não pertence ao produto.")
                return cleaned_data

            estoque_limite = int(variacao.quantidade or 0)
            if (
                self.instance
                and self.instance.pk
                and self.instance.variacao_id == variacao.id
            ):
                estoque_limite += int(self.instance.quantidade or 0)

            if quantidade > estoque_limite:
                self.add_error(
                    "quantidade",
                    f"Estoque disponível para esta variação: {estoque_limite}."
                )
        else:
            if variacao:
                self.add_error("variacao", "Este produto não usa variações.")
                return cleaned_data

            estoque_limite = int(produto.estoque_disponivel or 0)
            if (
                self.instance
                and self.instance.pk
                and self.instance.produto_id == produto.id
                and not self.instance.variacao_id
            ):
                estoque_limite += int(self.instance.quantidade or 0)

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

    def save(self, commit=True):
        instance = super().save(commit=False)
        produto = self.cleaned_data.get("produto")
        variacao = self.cleaned_data.get("variacao")
        quantidade = self.cleaned_data.get("quantidade") or 0

        instance.produto = produto
        instance.variacao = variacao if produto and produto.usa_variacoes else None
        instance.preco_unitario = self.cleaned_data.get("preco_unitario") or produto.valor_venda
        instance.subtotal = (
            Decimal(instance.preco_unitario) * Decimal(quantidade)
        ).quantize(Decimal("0.01"))

        if commit:
            instance.save()

        return instance


VendaItemFormSet = inlineformset_factory(
    Venda,
    VendaItem,
    form=VendaItemForm,
    extra=1,
    can_delete=True,
)