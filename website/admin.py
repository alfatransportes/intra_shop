# website/admin.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import (ConfigWebsite, FormaPagamento, NivelAvaria, Produto,
                     ProdutoImagem, Tipo, Unidade, Venda, VendaItem)

# -----------------------
# ConfigWebsite (mantido)
# -----------------------

class ConfigWebsiteForm(forms.ModelForm):
    class Meta:
        model = ConfigWebsite
        fields = "__all__"
        widgets = {
            "cor_destaque": forms.TextInput(attrs={"type": "color"}),
        }


@admin.register(ConfigWebsite)
class ConfigWebsiteAdmin(admin.ModelAdmin):
    form = ConfigWebsiteForm
    list_display = (
        "titulo",
        "cor_destaque_colorida",
        "preview_logo",
        "preview_favicon",
        "active",
    )
    search_fields = ("titulo",)
    list_filter = ("active",)
    ordering = ("titulo",)
    list_per_page = 25
    readonly_fields = ("preview_logo", "preview_favicon")

    fieldsets = (
        ("Informações gerais", {
            "fields": (
                "titulo",
                "cor_destaque",
            ),
            "description": "Configure o título e a cor de destaque usada no site."
        }),
        ("Imagens", {
            "fields": (
                "logo",
                "preview_logo",
                "favicon",
                "preview_favicon",
            ),
            "description": "Envie o logotipo e o favicon nos formatos e dimensões adequados."
        }),
        ("Status", {
            "fields": ("active",),
            "description": "Apenas uma configuração pode estar ativa por vez."
        }),
    )

    @admin.display(description="Cor destaque")
    def cor_destaque_colorida(self, obj):
        cor = getattr(obj, "cor_destaque", "#000000")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor,
            cor,
        )

    @admin.display(description="Logo")
    def preview_logo(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="120" style="border-radius:6px;">',
                obj.logo.url
            )
        return "—"

    @admin.display(description="Favicon")
    def preview_favicon(self, obj):
        if obj.favicon:
            return format_html(
                '<img src="{}" width="32" height="32" style="border-radius:4px;">',
                obj.favicon.url
            )
        return "—"


# -----------------------
# Cadastros simples
# -----------------------

@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "filial", "ativa")
    search_fields = ("codigo", "nome")
    list_filter = ("filial", "ativa")
    ordering = ("codigo",)
    list_per_page = 25


@admin.register(Tipo)
class TipoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)
    list_per_page = 25


@admin.register(NivelAvaria)
class NivelAvariaAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)
    list_per_page = 25


# -----------------------
# ProdutoImagem (Inline)
# -----------------------

class ProdutoImagemInline(admin.TabularInline):
    model = ProdutoImagem
    extra = 1
    fields = ("preview", "imagem", "legenda", "ordem", "principal")
    readonly_fields = ("preview",)
    ordering = ("ordem", "id")

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj and getattr(obj, "imagem", None):
            try:
                return format_html(
                    '<img src="{}" style="height:60px; border-radius:6px; object-fit:cover;" />',
                    obj.imagem.url
                )
            except Exception:
                return "—"
        return "—"


# -----------------------
# Produto
# -----------------------

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "quantidade",
        "unidade_prod",
        "tipo_prod",
        "nivel_ava_prod",
        "valor_nota",
        "porcen_desconto",
        "valor_venda",
    )
    search_fields = (
        "nome",
        "unidade_prod__nome",
        "tipo_prod__nome",
        "nivel_ava_prod__nome",
    )
    list_filter = (
        "unidade_prod",
        "tipo_prod",
        "nivel_ava_prod",
    )
    ordering = ("nome",)
    list_per_page = 25

    autocomplete_fields = ("unidade_prod", "tipo_prod", "nivel_ava_prod")
    readonly_fields = ("valor_venda",)
    inlines = (ProdutoImagemInline,)

    fieldsets = (
        ("Informações do produto", {
            "fields": ("nome", "quantidade", "unidade_prod", "tipo_prod", "nivel_ava_prod"),
        }),
        ("Valores", {
            "fields": ("valor_nota", "porcen_desconto", "valor_venda"),
        }),
    )


# -----------------------
# ProdutoImagem (opcional registrar separado)
# -----------------------

@admin.register(ProdutoImagem)
class ProdutoImagemAdmin(admin.ModelAdmin):
    list_display = ("id", "produto", "ordem", "principal", "thumb", "legenda")
    search_fields = ("produto__nome", "legenda", "imagem")
    list_filter = ("principal",)
    ordering = ("produto", "ordem", "id")
    list_per_page = 25
    autocomplete_fields = ("produto",)

    @admin.display(description="Thumb")
    def thumb(self, obj):
        if obj.imagem:
            return format_html(
                '<img src="{}" style="height:45px; border-radius:6px; object-fit:cover;" />',
                obj.imagem.url
            )
        return "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.principal and obj.produto_id:
            ProdutoImagem.objects.filter(
                produto_id=obj.produto_id
            ).exclude(pk=obj.pk).update(principal=False)


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome",)

class VendaItemInline(admin.TabularInline):
    model = VendaItem
    extra = 0
    readonly_fields = ("produto", "quantidade", "preco_unitario", "subtotal")
    can_delete = False

@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "status", "forma_pagamento", "total", "criado_em")
    list_filter = ("status", "forma_pagamento", "criado_em")
    search_fields = ("id", "usuario__username", "usuario__email")
    inlines = [VendaItemInline]
    actions = ["confirmar_vendas", "cancelar_vendas"]

    @admin.action(description="Marcar como CONFIRMADA")
    def confirmar_vendas(self, request, queryset):
        queryset.update(status="CONFIRMADA")

    @admin.action(description="Marcar como CANCELADA (não devolve estoque)")
    def cancelar_vendas(self, request, queryset):
        queryset.update(status="CANCELADA")