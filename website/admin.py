# website/admin.py
from decimal import Decimal

from django.contrib import admin
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Coalesce
from django.utils.html import format_html

from .models import (BannerConfigWebsite, Carrinho, CarrinhoItem,
                     ConfigWebsite, FormaPagamento, NivelAvaria, Pagamento,
                     Produto, ProdutoImagem, RegraParcelamentoVale, Tipo,
                     Unidade, Venda, VendaItem)


# -------------------------
# Config Website
# -------------------------
class BannerConfigWebsiteInline(admin.StackedInline):
    model = BannerConfigWebsite
    extra = 1
    fields = (
        "ordem",
        "ativo",
        "titulo",
        "subtitulo",
        "link",
        "banner",
        "preview_banner",
    )
    readonly_fields = ("preview_banner",)
    ordering = ("ordem", "id")

    def preview_banner(self, obj):
        if obj and obj.banner:
            return format_html(
                '<img src="{}" style="max-height:120px; border-radius:8px;" />',
                obj.banner.url,
            )
        return "Sem imagem"

    preview_banner.short_description = "Pré-visualização"


@admin.register(ConfigWebsite)
class ConfigWebsiteAdmin(admin.ModelAdmin):
    list_display = ("titulo", "active", "cor_destaque")
    list_filter = ("active",)
    search_fields = ("titulo",)
    ordering = ("titulo",)
    inlines = [BannerConfigWebsiteInline]


# -------------------------
# Cadastros base
# -------------------------
@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Tipo)
class TipoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(NivelAvaria)
class NivelAvariaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)
    ordering = ("nome",)


# -------------------------
# Produto e imagens
# -------------------------
class ProdutoImagemInline(admin.TabularInline):
    model = ProdutoImagem
    extra = 0
    fields = ("imagem", "legenda", "ordem", "principal")
    ordering = ("ordem", "id")


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    inlines = [ProdutoImagemInline]

    list_display = (
        "id",
        "nome",
        "tipo_prod",
        "unidade_prod",
        "nivel_ava_prod",
        "quantidade",
        "valor_nota",
        "porcen_desconto",
        "valor_venda",
    )
    list_filter = ("tipo_prod", "unidade_prod", "nivel_ava_prod")
    search_fields = ("nome", "descricao")
    ordering = ("nome",)
    readonly_fields = ("valor_venda",)


@admin.register(ProdutoImagem)
class ProdutoImagemAdmin(admin.ModelAdmin):
    list_display = ("id", "produto", "legenda", "ordem", "principal")
    list_filter = ("principal",)
    search_fields = ("produto__nome", "legenda")
    ordering = ("produto", "ordem", "id")


# -------------------------
# Carrinho
# -------------------------
class CarrinhoItemInline(admin.TabularInline):
    model = CarrinhoItem
    extra = 0
    fields = ("produto", "quantidade", "preco_unitario", "criado_em", "atualizado_em")
    readonly_fields = ("criado_em", "atualizado_em")
    autocomplete_fields = ("produto",)


@admin.register(Carrinho)
class CarrinhoAdmin(admin.ModelAdmin):
    inlines = [CarrinhoItemInline]

    list_display = ("id", "usuario", "status", "total_itens_calc", "total_valor_calc", "criado_em", "atualizado_em")
    list_filter = ("status",)
    search_fields = ("usuario__email", "usuario__username")
    ordering = ("-criado_em",)
    readonly_fields = ("criado_em", "atualizado_em")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.annotate(
            _total_itens=Coalesce(
                Sum("itens__quantidade"),
                0
            ),
            _total_valor=Coalesce(
                Sum(
                    F("itens__quantidade") * F("itens__preco_unitario"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

    @admin.display(description="Itens")
    def total_itens_calc(self, obj):
        return int(getattr(obj, "_total_itens", 0) or 0)

    @admin.display(description="Total (R$)")
    def total_valor_calc(self, obj):
        return getattr(obj, "_total_valor", 0)


@admin.register(CarrinhoItem)
class CarrinhoItemAdmin(admin.ModelAdmin):
    list_display = ("id", "carrinho", "produto", "quantidade", "preco_unitario", "criado_em", "atualizado_em")
    list_filter = ("carrinho__status",)
    search_fields = ("produto__nome", "carrinho__usuario__email")
    ordering = ("-atualizado_em",)
    readonly_fields = ("criado_em", "atualizado_em")
    autocomplete_fields = ("produto", "carrinho")


# -------------------------
# Pagamentos
# -------------------------
class RegraParcelamentoValeAdmin(admin.ModelAdmin):
    list_display = ("id", "minimo", "maximo", "max_parcelas", "ativo")
    list_filter = ("ativo",)
    ordering = ("minimo",)
    search_fields = ("minimo", "maximo")


admin.site.register(RegraParcelamentoVale, RegraParcelamentoValeAdmin)


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo", "ativa")
    list_filter = ("ativa", "codigo")
    ordering = ("codigo",)

    fieldsets = (
        (None, {"fields": ("codigo", "ativa")}),
        ("Pix (se aplicável)", {"fields": ("pix_chave", "pix_nome", "pix_cidade", "pix_payload")}),
    )


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ("id", "venda", "tipo", "parcelas", "criado_em")
    list_filter = ("tipo",)
    search_fields = ("venda__id", "venda__usuario__email")
    ordering = ("-criado_em",)
    readonly_fields = ("criado_em",)


# -------------------------
# Vendas
# -------------------------
class VendaItemInline(admin.TabularInline):
    model = VendaItem
    extra = 0
    fields = ("produto", "quantidade", "preco_unitario", "subtotal")
    readonly_fields = ("preco_unitario", "subtotal")
    autocomplete_fields = ("produto",)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    inlines = [VendaItemInline]

    list_display = ("id", "usuario", "status", "forma_pagamento", "total", "parcelas", "criado_em")
    list_filter = ("status", "forma_pagamento")
    search_fields = ("id", "usuario__email", "usuario__username")
    ordering = ("-criado_em",)
    readonly_fields = ("total", "criado_em", "atualizado_em")

    fields = (
        "usuario",
        "status",
        "forma_pagamento",
        "total",
        "parcelas",
        "minuta",
        "comprovante_pix",
        "comprovante_vale",
        "observacao",
        "criado_em",
        "atualizado_em",
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "forma_pagamento":
            kwargs["queryset"] = FormaPagamento.objects.filter(ativa=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalcular_total()