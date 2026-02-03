# website/admin.py
from decimal import ROUND_HALF_UP, Decimal

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import (Carrinho, CarrinhoItem, ConfigWebsite, FormaPagamento,
                     NivelAvaria, Produto, ProdutoImagem,
                     RegraParcelamentoVale, Tipo, Unidade, Venda, VendaItem)

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

class RegraParcelamentoValeInline(admin.TabularInline):
    model = RegraParcelamentoVale
    extra = 1
    fields = ("valor_ate", "max_parcelas")
    ordering = ("valor_ate",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("valor_ate")

@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ("nome_admin", "codigo", "ativa")
    list_filter = ("codigo", "ativa")
    search_fields = ("codigo", "pix_chave", "pix_nome", "pix_cidade", "pix_copia_cola")
    ordering = ("codigo",)
    inlines = [RegraParcelamentoValeInline]  # ✅ AQUI

    fieldsets = (
        ("Dados básicos", {
            "fields": ("codigo", "ativa"),
        }),
        ("Configuração Pix", {
            "fields": ("pix_chave", "pix_nome", "pix_cidade", "pix_copia_cola"),
            "description": "Preencha apenas se a forma for PIX.",
        }),
        ("Parcelamento (Vale)", {
            "fields": (),
            "description": "Cadastre as regras no quadro abaixo: até R$ X → máximo Y parcelas (apenas para VALE).",
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


class VendaAdminForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()

        status = cleaned.get("status")
        fp = cleaned.get("forma_pagamento")
        comp_pix = cleaned.get("comprovante_pix")
        comp_vale = cleaned.get("comprovante_vale")

        # Só valida se estiver tentando CONFIRMAR
        if status == Venda.Status.CONFIRMADA and fp:
            codigo = fp.codigo

            if codigo == FormaPagamento.Codigo.PIX and not comp_pix:
                self.add_error("comprovante_pix", "Obrigatório anexar o comprovante do PIX para confirmar.")
                raise ValidationError("Não é possível confirmar sem comprovante do PIX.")

            if codigo == FormaPagamento.Codigo.VALE and not comp_vale:
                self.add_error("comprovante_vale", "Obrigatório anexar o comprovante do VALE para confirmar.")
                raise ValidationError("Não é possível confirmar sem comprovante do VALE.")

        return cleaned


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    form = VendaAdminForm  # ✅ AQUI

    list_display = (
        "id",
        "usuario",
        "status_badge",
        "forma_pagamento",
        "parcelas_admin",
        "total",
        "criado_em",
        "comprovante_link",
    )

    list_filter = ("status", "forma_pagamento", "criado_em")
    search_fields = ("id", "usuario__email", "usuario__numero_cracha")
    ordering = ("-id",)
    inlines = [VendaItemInline]
    actions = ["confirmar_vendas", "cancelar_vendas"]
    readonly_fields = ("total", "criado_em", "parcelas")

    fieldsets = (
        ("Venda", {"fields": ("usuario", "status", "forma_pagamento", "parcelas", "total", "criado_em")}),
        ("PIX", {"fields": ("comprovante_pix",), "description": "Apenas para pagamentos via Pix."}),
        ("VALE", {"fields": ("comprovante_vale",), "description": "Apenas para pagamentos via Vale."}),
        ("Observação", {"fields": ("observacao",)}),
    )


    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.status == Venda.Status.PENDENTE:
            return format_html('<span class="badge" style="background:#f59e0b;color:#111827;">Pendente</span>')
        if obj.status == Venda.Status.CONFIRMADA:
            return format_html('<span class="badge" style="background:#16a34a;">Confirmada</span>')
        if obj.status == Venda.Status.CANCELADA:
            return format_html('<span class="badge" style="background:#dc2626;">Cancelada</span>')
        return obj.status

    @admin.display(description="Comprovantes")
    def comprovante_link(self, obj):
        links = []
        if obj.comprovante_pix:
            try:
                links.append(format_html(
                    '<a href="{}" target="_blank" rel="noopener">Pix</a>',
                    obj.comprovante_pix.url
                ))
            except Exception:
                pass
        if obj.comprovante_vale:
            try:
                links.append(format_html(
                    '<a href="{}" target="_blank" rel="noopener">Vale</a>',
                    obj.comprovante_vale.url
                ))
            except Exception:
                pass
        return format_html(" • ".join([str(x) for x in links])) if links else "—"

    @admin.action(description="Marcar como CONFIRMADA")
    def confirmar_vendas(self, request, queryset):
        bloqueadas = []
        confirmadas = 0

        for v in queryset.select_related("forma_pagamento"):
            codigo = v.forma_pagamento.codigo

            if codigo == FormaPagamento.Codigo.PIX and not v.comprovante_pix:
                bloqueadas.append(v.id)
                continue

            if codigo == FormaPagamento.Codigo.VALE and not v.comprovante_vale:
                bloqueadas.append(v.id)
                continue

            if v.status != Venda.Status.CONFIRMADA:
                v.status = Venda.Status.CONFIRMADA
                v.save(update_fields=["status"])
                confirmadas += 1

        if confirmadas:
            self.message_user(request, f"{confirmadas} venda(s) confirmada(s) com sucesso.", level=messages.SUCCESS)

        if bloqueadas:
            self.message_user(
                request,
                "Não foi possível confirmar (faltando comprovante) nos pedidos: " + ", ".join(map(str, bloqueadas)),
                level=messages.ERROR,
            )


    @admin.display(description="Parcelamento")
    def parcelas_admin(self, obj):
        if obj.forma_pagamento and obj.forma_pagamento.codigo == FormaPagamento.Codigo.VALE:
            p = int(obj.parcelas or 1)
            if p <= 0:
                p = 1
            valor = (obj.total / Decimal(p)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return f"{p}x de R$ {valor}"
        return "—"


    @admin.action(description="Marcar como CANCELADA (não devolve estoque)")
    def cancelar_vendas(self, request, queryset):
        queryset.update(status=Venda.Status.CANCELADA)
