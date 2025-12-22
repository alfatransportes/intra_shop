from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import ConfigWebsite, NivelAvaria, Produto, Tipo, Unidade


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


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
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

    # Melhora MUITO a UX se você tem muita Unidade/Tipo/Nível
    autocomplete_fields = ("unidade_prod", "tipo_prod", "nivel_ava_prod")

    fieldsets = (
        ("Informações do produto", {
            "fields": ("nome", "unidade_prod", "tipo_prod", "nivel_ava_prod"),
        }),
        ("Valores", {
            "fields": ("valor_nota", "porcen_desconto", "valor_venda"),
        }),
    )
