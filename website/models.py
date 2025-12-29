
# website/models.py
import os
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.text import slugify
from PIL import Image, ImageOps


def upload_to(instance, filename):
    base, _ext = os.path.splitext(filename)
    return f"produtos/{base}.webp"


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
    quantidade = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade",
        help_text="Quantidade em estoque (mínimo 1).",
    )

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
    
    @property
    def estoque_disponivel(self):
        reservado = (
            self.itens_carrinho
            .filter(carrinho__status="ABERTO")
            .aggregate(q=Coalesce(Sum("quantidade"), 0))["q"]
        )
        return max((self.quantidade or 0) - int(reservado), 0)


class ProdutoImagem(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="imagens",
    )
    imagem = models.ImageField(upload_to=upload_to)
    legenda = models.CharField(max_length=120, blank=True)
    ordem = models.PositiveIntegerField(default=0)
    principal = models.BooleanField(default=False)

    class Meta:
        ordering = ["ordem", "id"]

    def save(self, *args, **kwargs):
        # 1) Se não tem arquivo, segue normal
        if not self.imagem:
            return super().save(*args, **kwargs)

        # 2) Se já é webp, segue normal
        original_name = self.imagem.name or ""
        if original_name.lower().endswith(".webp"):
            return super().save(*args, **kwargs)

        # 3) Evita reconverter em updates quando a imagem não mudou
        #    (só tenta comparar se já existe no banco)
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).only("imagem").first()
            if old and old.imagem and old.imagem.name == self.imagem.name:
                return super().save(*args, **kwargs)

        # 4) Abre a imagem e corrige rotação via EXIF
        self.imagem.seek(0)
        img = Image.open(self.imagem)
        img = ImageOps.exif_transpose(img)

        # 5) Normaliza modos:
        #    - preserva alpha se existir
        #    - trata paletas (PNG P) e outros modos
        if img.mode in ("RGBA", "LA"):
            converted = img.convert("RGBA")
        elif img.mode == "P":
            # pode ter transparência; converte para RGBA para não perder
            converted = img.convert("RGBA")
        else:
            converted = img.convert("RGB")

        # 6) Salva em buffer como WebP
        buffer = BytesIO()
        converted.save(
            buffer,
            format="WEBP",
            quality=80,
            method=6,
            # Se quiser reduzir ainda mais tamanho (perde qualidade):
            # optimize=True,
        )
        buffer.seek(0)

        # 7) Grava no ImageField sem salvar 2x no banco
        base, _ext = os.path.splitext(os.path.basename(original_name))
        new_name = f"{base}.webp"

        self.imagem.save(new_name, ContentFile(buffer.read()), save=False)

        # (Opcional) se você quiser remover o arquivo antigo do storage,
        # faça depois do super().save e com cuidado, pra não apagar se der erro.
        # old_name = original_name

        return super().save(*args, **kwargs)




class Carrinho(models.Model):
    class Status(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        FECHADO = "FECHADO", "Fechado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carrinhos",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ABERTO,
        db_index=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "status"],
                condition=models.Q(status="ABERTO"),
                name="unique_carrinho_aberto_por_usuario",
            )
        ]

    def __str__(self):
        return f"Carrinho {self.id} - {self.usuario} ({self.status})"

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.itens.all()), Decimal("0.00"))

    @property
    def total_itens(self) -> int:
        return sum(item.quantidade for item in self.itens.all())


class CarrinhoItem(models.Model):
    carrinho = models.ForeignKey("Carrinho", on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("Produto", on_delete=models.PROTECT, related_name="itens_carrinho")  # <= aqui
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("carrinho", "produto")

    def __str__(self):
        return f"{self.produto.nome} x {self.quantidade}"

    def save(self, *args, **kwargs):
        # garante que o preço do item fica “congelado” no valor_venda do produto no momento
        if not self.preco_unitario or self.preco_unitario <= 0:
            self.preco_unitario = self.produto.valor_venda
        super().save(*args, **kwargs)

    @property
    def subtotal(self) -> Decimal:
        return (self.preco_unitario * Decimal(self.quantidade)).quantize(Decimal("0.01"))



from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class FormaPagamento(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Venda(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vendas")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.PROTECT, related_name="vendas")
    criado_em = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True, default="")

    # opcional (congelar total):
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Venda #{self.pk} - {self.usuario} - {self.status}"


class VendaItem(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("Produto", on_delete=models.PROTECT, related_name="itens_venda")
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    def save(self, *args, **kwargs):
        self.subtotal = (self.preco_unitario * self.quantidade).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.produto} x{self.quantidade}"