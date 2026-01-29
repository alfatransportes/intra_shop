# website/admin.py
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (Carrinho, CarrinhoItem, ConfigWebsite, FormaPagamento,
                     NivelAvaria, Produto, ProdutoImagem, Tipo, Unidade, Venda,
                     VendaItem)

# -----------------------
# ConfigWebsite (mantido)
# -----------------------

class ConfigWebsiteForm(forms.ModelForm):
    class Meta:
        model = ConfigWebsite
        fields = "__all__"
        widgets = {"cor_destaque": forms.TextInput(attrs={"type": "color"})}


@admin.register(ConfigWebsite)
class ConfigWebsiteAdmin(admin.ModelAdmin):
    form = ConfigWebsiteForm
    list_display = ("titulo", "cor_destaque_colorida", "preview_logo", "preview_favicon", "active")
    search_fields = ("titulo",)
    list_filter = ("active",)
    ordering = ("titulo",)
    list_per_page = 25
    readonly_fields = ("preview_logo", "preview_favicon")

    fieldsets = (
        ("Informações gerais", {
            "fields": ("titulo", "cor_destaque"),
            "description": "Configure o título e a cor de destaque usada no site.",
        }),
        ("Imagens", {
            "fields": ("logo", "preview_logo", "favicon", "preview_favicon"),
            "description": "Envie o logotipo e o favicon nos formatos e dimensões adequados.",
        }),
        ("Status", {
            "fields": ("active",),
            "description": "Apenas uma configuração pode estar ativa por vez.",
        }),
    )

    @admin.display(description="Cor destaque")
    def cor_destaque_colorida(self, obj):
        cor = getattr(obj, "cor_destaque", "#000000")
        return format_html('<span style="color:{}; font-weight:bold;">{}</span>', cor, cor)

    @admin.display(description="Logo")
    def preview_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="120" style="border-radius:6px;">', obj.logo.url)
        return "—"

    @admin.display(description="Favicon")
    def preview_favicon(self, obj):
        if obj.favicon:
            return format_html('<img src="{}" width="32" height="32" style="border-radius:4px;">', obj.favicon.url)
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
                    obj.imagem.url,
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
        "numero_bo",
        "nome",
        "unidade_prod",
        "tipo_prod",
        "nivel_ava_prod",
        "quantidade",
        "estoque_disponivel_admin",
        "valor_nota",
        "porcen_desconto",
        "valor_venda",
        "imagem_principal_admin",
    )
    search_fields = (
        "numero_bo",
        "nome",
        "descricao",
        "unidade_prod__nome",
        "tipo_prod__nome",
        "nivel_ava_prod__nome",
    )
    list_filter = ("unidade_prod", "tipo_prod", "nivel_ava_prod")
    ordering = ("-id",)
    list_per_page = 25

    autocomplete_fields = ("unidade_prod", "tipo_prod", "nivel_ava_prod")
    readonly_fields = ("valor_venda",)
    inlines = (ProdutoImagemInline,)

    fieldsets = (
        ("Informações do produto", {
            "fields": (
                "numero_bo",
                "nome",
                "descricao",
                "unidade_prod",
                "tipo_prod",
                "nivel_ava_prod",
                "quantidade",
            ),
        }),
        ("Valores", {"fields": ("valor_nota", "porcen_desconto", "valor_venda")}),
    )

    @admin.display(description="Estoque disponível", ordering="quantidade")
    def estoque_disponivel_admin(self, obj):
        return obj.estoque_disponivel

    @admin.display(description="Imagem principal")
    def imagem_principal_admin(self, obj):
        img = obj.imagens.filter(principal=True).first() or obj.imagens.order_by("ordem", "id").first()
        if img and img.imagem:
            return format_html(
                '<img src="{}" style="height:45px; width:45px; border-radius:6px; object-fit:cover;" />',
                img.imagem.url,
            )
        return "—"


# -----------------------
# ProdutoImagem (registrado separado)
# -----------------------

@admin.register(ProdutoImagem)
class ProdutoImagemAdmin(admin.ModelAdmin):
    list_display = ("id", "produto", "ordem", "principal", "thumb", "legenda")
    search_fields = ("produto__nome", "legenda")
    list_filter = ("principal",)
    ordering = ("produto", "ordem", "id")
    list_per_page = 25
    autocomplete_fields = ("produto",)

    @admin.display(description="Thumb")
    def thumb(self, obj):
        if obj.imagem:
            return format_html(
                '<img src="{}" style="height:45px; border-radius:6px; object-fit:cover;" />',
                obj.imagem.url,
            )
        return "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.principal and obj.produto_id:
            ProdutoImagem.objects.filter(produto_id=obj.produto_id).exclude(pk=obj.pk).update(principal=False)


# -----------------------
# Carrinho / Itens
# -----------------------

class CarrinhoItemInline(admin.TabularInline):
    model = CarrinhoItem
    extra = 0
    autocomplete_fields = ("produto",)
    fields = ("produto", "quantidade", "preco_unitario", "subtotal_admin", "criado_em", "expira_em_admin", "expirado_admin")
    readonly_fields = ("subtotal_admin", "criado_em", "expira_em_admin", "expirado_admin")

    @admin.display(description="Subtotal")
    def subtotal_admin(self, obj):
        return obj.subtotal

    @admin.display(description="Expira em")
    def expira_em_admin(self, obj):
        return obj.expira_em

    @admin.display(description="Status")
    def expirado_admin(self, obj):
        if obj.expirado:
            return format_html('<span style="color:#b91c1c;font-weight:600;">Expirado</span>')
        return format_html('<span style="color:#15803d;font-weight:600;">Ativo</span>')


@admin.register(Carrinho)
class CarrinhoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "status", "criado_em", "total_itens_admin", "total_valor_admin")
    list_filter = ("status", "criado_em")
    search_fields = ("usuario__email", "usuario__numero_cracha")
    ordering = ("-id",)
    inlines = (CarrinhoItemInline,)
    autocomplete_fields = ("usuario",)

    @admin.display(description="Total itens")
    def total_itens_admin(self, obj):
        return obj.total_itens

    @admin.display(description="Total (R$)")
    def total_valor_admin(self, obj):
        return obj.total_valor


@admin.register(CarrinhoItem)
class CarrinhoItemAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario_admin", "carrinho", "produto", "quantidade", "preco_unitario", "subtotal", "criado_em", "atualizado_em", "expirado_admin")
    list_filter = ("carrinho__status", "criado_em")
    search_fields = ("produto__nome", "carrinho__usuario__email", "carrinho__usuario__numero_cracha")
    autocomplete_fields = ("carrinho", "produto")
    ordering = ("-id",)

    fields = ("carrinho", "produto", "quantidade", "preco_unitario", "subtotal", "criado_em", "atualizado_em")
    readonly_fields = ("subtotal", "criado_em", "atualizado_em")

    @admin.display(description="Usuário")
    def usuario_admin(self, obj):
        return getattr(obj.carrinho, "usuario", None)

    @admin.display(description="Expirado?")
    def expirado_admin(self, obj):
        return "Sim" if obj.expirado else "Não"


# -----------------------
# FormaPagamento
# -----------------------

@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ("nome_admin", "codigo", "ativa")
    list_filter = ("codigo", "ativa")
    search_fields = ("codigo", "pix_chave", "pix_nome", "pix_cidade", "pix_copia_cola")
    ordering = ("codigo",)

    fieldsets = (
        ("Dados básicos", {
            "fields": ("codigo", "ativa"),
        }),
        ("Configuração Pix", {
            "fields": ("pix_chave", "pix_nome", "pix_cidade", "pix_copia_cola"),
            "description": "Preencha apenas se a forma for PIX.",
        }),
    )

    @admin.display(description="Forma")
    def nome_admin(self, obj):
        return obj.get_codigo_display()

# -----------------------
# Venda / Itens
# -----------------------

class VendaItemInline(admin.TabularInline):
    model = VendaItem
    extra = 0
    readonly_fields = ("produto", "quantidade", "preco_unitario", "subtotal")
    can_delete = False


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "status_badge", "forma_pagamento", "total", "criado_em", "comprovante_link")
    list_filter = ("status", "forma_pagamento", "criado_em")
    search_fields = ("id", "usuario__email", "usuario__numero_cracha")
    ordering = ("-id",)
    inlines = [VendaItemInline]
    actions = ["confirmar_vendas", "cancelar_vendas"]
    readonly_fields = ("total", "criado_em")

    fieldsets = (
        ("Venda", {"fields": ("usuario", "status", "forma_pagamento", "total", "criado_em")}),
        ("PIX", {"fields": ("comprovante_pix",), "description": "Apenas para pagamentos via Pix."}),
        ("Observação", {"fields": ("observacao",)}),
    )

    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.status == "PENDENTE":
            return format_html('<span class="badge" style="background:#f59e0b;color:#111827;">Pendente</span>')
        if obj.status == "CONFIRMADA":
            return format_html('<span class="badge" style="background:#16a34a;">Confirmada</span>')
        if obj.status == "CANCELADA":
            return format_html('<span class="badge" style="background:#dc2626;">Cancelada</span>')
        return obj.status

    @admin.display(description="Comprovante")
    def comprovante_link(self, obj):
        if getattr(obj, "comprovante_pix", None):
            try:
                return format_html('<a href="{}" target="_blank">Ver</a>', obj.comprovante_pix.url)
            except Exception:
                return "—"
        return "—"

    @admin.action(description="Marcar como CONFIRMADA")
    def confirmar_vendas(self, request, queryset):
        queryset.update(status="CONFIRMADA")

    @admin.action(description="Marcar como CANCELADA (não devolve estoque)")
    def cancelar_vendas(self, request, queryset):
        queryset.update(status="CANCELADA")
