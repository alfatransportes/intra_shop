from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models
from django.utils.text import slugify
from PIL import Image


class ConfigWebsite(models.Model):
    titulo = models.CharField(
        max_length=50,
        verbose_name="Título da Configuração"
    )
    cor_destaque = models.CharField(
        max_length=7,
        verbose_name="Cor do título",
        help_text="Selecione uma cor destaque (ex: #DE1E3E).",
        default="#DE1E3E"
    )
    logo = models.FileField(
        upload_to="imagensConfiguracaoWebsite/",
        # validators=[validar_dimensoes_logo],
        verbose_name="Logotipo"
    )
    favicon = models.FileField(
        upload_to="imagensConfiguracaoWebsite/",
        verbose_name="Favicon"
    )
    active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuração do Website"
        verbose_name_plural = "Configurações do Website"
        ordering = ["titulo"]

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()

        # Limite de 3 registros
        if not self.pk and ConfigWebsite.objects.count() >= 3:
            raise ValidationError("Você só pode cadastrar no máximo 3 configurações.")

        # se o registro estiver ativo, verifica se já existe outro ativo
        if self.active:
            ativo_existente = ConfigWebsite.objects.filter(active=True).exclude(pk=self.pk).exists()
            if ativo_existente:
                raise ValidationError("Já existe uma configuração ativa. Desative-a antes de ativar outra.")

    def save(self, *args, **kwargs):
        if not self.pk and ConfigWebsite.objects.count() >= 3:
            raise ValidationError("Você só pode cadastrar no máximo 3 configurações.")
        super().save(*args, **kwargs)


class Unidade(models.Model):
    codigo = models.IntegerField()
    nome = models.CharField(max_length=255)
    filial = models.BooleanField(default=False)
    ativa = models.BooleanField(default=False)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return str(self.codigo)  # <- corrigido: precisa ser string


class Tipo(models.Model):
    nome = models.CharField(max_length=255)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class NivelAvaria(models.Model):
    nome = models.CharField(max_length=255)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Produto(models.Model):
    unidade_prod = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name="produtos",
        verbose_name="Unidade",
    )
    tipo_prod = models.ForeignKey(
        Tipo,
        on_delete=models.PROTECT,
        related_name="produtos",
        verbose_name="Tipo",
    )
    nivel_ava_prod = models.ForeignKey(
        NivelAvaria,
        on_delete=models.PROTECT,
        related_name="produtos",
        verbose_name="Nível de Avaria",
    )

    nome = models.CharField(max_length=255)

    valor_nota = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor da Nota",
    )

    porcen_desconto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        verbose_name="Desconto (%)",
        help_text="Informe um valor entre 0 e 100",
    )

    valor_venda = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor de Venda",
        editable=False,
    )

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.id} - {self.nome}"

    def save(self, *args, **kwargs):
        desconto = (self.porcen_desconto or Decimal("0")) / Decimal("100")
        self.valor_venda = (self.valor_nota * (Decimal("1") - desconto)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
        super().save(*args, **kwargs)


class ProdutoImagem(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="imagens",
    )
    imagem = models.ImageField(upload_to="produtos/")
    legenda = models.CharField(max_length=120, blank=True)
    ordem = models.PositiveIntegerField(default=0)
    principal = models.BooleanField(default=False)

    class Meta:
        ordering = ["ordem", "id"]