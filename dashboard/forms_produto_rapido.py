from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from website.models import Produto, ProdutoImagem, ProdutoVariacao


class BaseBootstrapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget
            current = widget.attrs.get("class", "")

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = f"{current} form-check-input".strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = f"{current} form-select".strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = f"{current} form-control".strip()
                widget.attrs.setdefault("rows", 4)
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = f"{current} form-control".strip()
            else:
                widget.attrs["class"] = f"{current} form-control".strip()


class ProdutoRapidoForm(BaseBootstrapForm):
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
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "ativo": forms.HiddenInput(),
        }

    def clean(self):
        cleaned = super().clean()

        valor_nota = cleaned.get("valor_nota")
        desconto = cleaned.get("porcen_desconto")
        usa_variacoes = bool(cleaned.get("usa_variacoes"))
        quantidade = int(cleaned.get("quantidade") or 0)
        ativo = bool(cleaned.get("ativo"))

        if valor_nota is not None and desconto is not None:
            try:
                desconto_decimal = (desconto or Decimal("0")) / Decimal("100")
                valor_venda = (valor_nota * (Decimal("1") - desconto_decimal)).quantize(Decimal("0.01"))
                if valor_venda <= 0:
                    self.add_error(
                        "porcen_desconto",
                        "O desconto deixou o valor de venda zerado ou negativo."
                    )
            except Exception:
                pass

        # draft pode ficar sem estoque; publicar não
        if ativo and (not usa_variacoes) and quantidade <= 0:
            self.add_error(
                "quantidade",
                "Para publicar um produto sem variações, informe quantidade maior que zero."
            )

        return cleaned


class ProdutoImagemRapidoForm(BaseBootstrapForm):
    class Meta:
        model = ProdutoImagem
        fields = ["imagem", "legenda", "ordem", "principal"]


class ProdutoVariacaoRapidoForm(BaseBootstrapForm):
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


class BaseProdutoImagemRapidoFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        imagens_validas = []
        principais = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            imagem = form.cleaned_data.get("imagem") or getattr(form.instance, "imagem", None)
            if imagem:
                imagens_validas.append(form)

            if form.cleaned_data.get("principal") and imagem:
                principais += 1

        if imagens_validas:
            if principais == 0:
                raise ValidationError("Marque uma imagem como principal.")
            if principais > 1:
                raise ValidationError("Apenas uma imagem pode ser principal.")


class BaseProdutoVariacaoRapidoFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        combinacoes = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            categoria = form.cleaned_data.get("categoria")
            genero = form.cleaned_data.get("genero")
            faixa_etaria = form.cleaned_data.get("faixa_etaria")
            tamanho = (form.cleaned_data.get("tamanho") or "").strip().upper() or None
            cor = (form.cleaned_data.get("cor") or "").strip() or None
            quantidade = int(form.cleaned_data.get("quantidade") or 0)
            ativo = bool(form.cleaned_data.get("ativo"))

            vazio_total = not any([categoria, genero, faixa_etaria, tamanho, cor, quantidade, ativo])
            if vazio_total:
                continue

            chave = (categoria, genero, faixa_etaria, tamanho, cor)
            if chave in combinacoes:
                raise ValidationError(
                    "Existem variações duplicadas. Não repita categoria/gênero/faixa etária/tamanho/cor."
                )
            combinacoes.add(chave)

            if quantidade > 0 and not tamanho:
                form.add_error("tamanho", "Informe o tamanho quando houver estoque.")


ProdutoImagemRapidoFormSet = inlineformset_factory(
    Produto,
    ProdutoImagem,
    form=ProdutoImagemRapidoForm,
    formset=BaseProdutoImagemRapidoFormSet,
    extra=1,
    can_delete=True,
)

ProdutoVariacaoRapidoFormSet = inlineformset_factory(
    Produto,
    ProdutoVariacao,
    form=ProdutoVariacaoRapidoForm,
    formset=BaseProdutoVariacaoRapidoFormSet,
    extra=1,
    can_delete=True,
)