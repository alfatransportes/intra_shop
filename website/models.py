# website/models.py
import os
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from PIL import Image, ImageOps

# Janela de reserva (carrinho) — itens fora dessa janela são considerados expirados
RESERVA_HORAS = 4


def upload_to(instance, filename):
    base, _ext = os.path.splitext(filename)
    return f"produtos/{base}.webp"



class ConfigWebsite(models.Model):
    titulo = models.CharField(max_length=50, verbose_name="Título da Configuração")
    cor_destaque = models.CharField(
        max_length=7,
        verbose_name="Cor do título",
        help_text="Selecione uma cor destaque (ex: #DE1E3E).",
        default="#DE1E3E",
    )
    logo = models.ImageField(
        upload_to="imagensConfiguracaoWebsite/",
        verbose_name="Logotipo",
    )
    favicon = models.ImageField(
        upload_to="imagensConfiguracaoWebsite/",
        verbose_name="Favicon",
    )
    image_auth = models.ImageField(
        upload_to="imagensConfiguracaoWebsite/",
        verbose_name="Imagem de Autenticação",
        blank=True,
        null=True,
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

        if not self.pk and ConfigWebsite.objects.count() >= 3:
            raise ValidationError("Você só pode cadastrar no máximo 3 configurações.")

        if self.active:
            ativo_existente = (
                ConfigWebsite.objects.filter(active=True)
                .exclude(pk=self.pk)
                .exists()
            )
            if ativo_existente:
                raise ValidationError(
                    "Já existe uma configuração ativa. Desative a outra antes de ativar esta."
                )


class BannerConfigWebsite(models.Model):
    config_website = models.ForeignKey(
        ConfigWebsite,
        on_delete=models.CASCADE,
        related_name="banners",
        verbose_name="Configuração do Website",
    )
    titulo = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        verbose_name="Título do banner",
    )
    subtitulo = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Subtítulo do banner",
    )
    link = models.URLField(
        blank=True,
        null=True,
        verbose_name="Link do banner",
    )
    banner = models.ImageField(
        upload_to="imagensBannersConfiguracaoWebsite/",
        verbose_name="Imagem do Banner",
    )
    ordem = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordem",
        help_text="Menor valor aparece primeiro no carrossel.",
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Banner da Configuração do Website"
        verbose_name_plural = "Banners da Configuração do Website"
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.config_website.titulo} - Banner {self.ordem}"

    def clean(self):
        super().clean()

        if self.config_website_id:
            total_banners = BannerConfigWebsite.objects.filter(
                config_website=self.config_website
            ).exclude(pk=self.pk).count()

            if total_banners >= 10:
                raise ValidationError(
                    "Cada configuração pode ter no máximo 10 banners no carrossel."
                )

    def _imagem_foi_alterada(self):
        if not self.pk:
            return True

        antigo = type(self).objects.filter(pk=self.pk).only("banner").first()
        if not antigo:
            return True

        nome_antigo = antigo.banner.name if antigo.banner else None
        nome_atual = self.banner.name if self.banner else None

        return nome_antigo != nome_atual

    def _gerar_banner_webp(self):
        self.banner.seek(0)

        largura_final = 1920
        altura_final = 700

        with Image.open(self.banner) as img:
            img = ImageOps.exif_transpose(img)

            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            largura, altura = img.size
            proporcao_original = largura / altura
            proporcao_final = largura_final / altura_final

            # cortar imagem para manter proporção correta
            if proporcao_original > proporcao_final:
                # imagem muito larga
                nova_largura = int(altura * proporcao_final)
                offset = (largura - nova_largura) // 2
                box = (offset, 0, offset + nova_largura, altura)
            else:
                # imagem muito alta
                nova_altura = int(largura / proporcao_final)
                offset = (altura - nova_altura) // 2
                box = (0, offset, largura, offset + nova_altura)

            img = img.crop(box)

            # redimensiona para tamanho final
            img = img.resize((largura_final, altura_final), Image.LANCZOS)

            buffer = BytesIO()

            img.save(
                buffer,
                format="WEBP",
                quality=85,
                method=6,
                optimize=True,
            )

            buffer.seek(0)

        nome_base, _ = os.path.splitext(os.path.basename(self.banner.name))
        nome_unico = f"{nome_base}_{uuid.uuid4().hex[:10]}.webp"

        return nome_unico, ContentFile(buffer.read())

    def save(self, *args, **kwargs):
        if not self.banner:
            return super().save(*args, **kwargs)

        arquivo_antigo = None
        if self.pk:
            antigo = type(self).objects.filter(pk=self.pk).only("banner").first()
            if antigo and antigo.banner:
                arquivo_antigo = antigo.banner.name

        if self._imagem_foi_alterada():
            novo_nome, novo_arquivo = self._gerar_banner_webp()
            self.banner.save(novo_nome, novo_arquivo, save=False)

        super().save(*args, **kwargs)

        if (
            arquivo_antigo
            and arquivo_antigo != self.banner.name
            and self.banner.storage.exists(arquivo_antigo)
        ):
            self.banner.storage.delete(arquivo_antigo)

    def delete(self, *args, **kwargs):
        arquivo = self.banner.name if self.banner else None
        storage = self.banner.storage if self.banner else None

        super().delete(*args, **kwargs)

        if arquivo and storage and storage.exists(arquivo):
            storage.delete(arquivo)

class Unidade(models.Model):
    codigo = models.IntegerField(blank=True, null=True)
    nome = models.CharField(max_length=255)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Tipo(models.Model):
    nome = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)

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

    num_controle = models.CharField(max_length=255, null=True, blank=True, verbose_name="Número de Controle")
    nome = models.CharField(max_length=255)
    quantidade = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade",
        help_text="Quantidade em estoque (mínimo 1).",
    )
    maximo_por_usuario = models.PositiveIntegerField(
        default=0,
        verbose_name="Quantidade máxima por usuário",
        help_text="0 = sem limite por usuário.",
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
    descricao = models.TextField(verbose_name="Descrição do produto")

    ativo = models.BooleanField(default=False, verbose_name="Ativo para venda")

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.id} - {self.nome}"

    def save(self, *args, **kwargs):
        desconto = (self.porcen_desconto or Decimal("0")) / Decimal("100")
        self.valor_venda = (self.valor_nota * (Decimal("1") - desconto)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        super().save(*args, **kwargs)

        # Se estiver ativo mas sem imagens, desativa automaticamente
        if self.ativo and not self.imagens.exists():
            self.ativo = False
            super().save(update_fields=["ativo"])

    @property
    def estoque_disponivel(self) -> int:
        """
        Estoque disponível = estoque físico - reservado em carrinhos ABERTOS
        (considerando apenas itens não expirados).
        """
        limite = timezone.now() - timedelta(hours=RESERVA_HORAS)
        reservado = (
            self.itens_carrinho.filter(
                carrinho__status="ABERTO",
                atualizado_em__gte=limite,
            ).aggregate(q=Coalesce(Sum("quantidade"), 0))["q"]
        )
        return max((self.quantidade or 0) - int(reservado or 0), 0)
    
    def quantidade_ja_solicitada_por_usuario(self, usuario) -> int:
        if not usuario or not usuario.is_authenticated:
            return 0

        total = self.itens_venda.filter(
            venda__usuario=usuario
        ).exclude(
            venda__status="CANCELADA"
        ).aggregate(
            total=Coalesce(Sum("quantidade"), 0)
        )["total"]

        return int(total or 0)


    def quantidade_no_carrinho_aberto(self, usuario) -> int:
        if not usuario or not usuario.is_authenticated:
            return 0

        total = self.itens_carrinho.filter(
            carrinho__usuario=usuario,
            carrinho__status="ABERTO",
        ).aggregate(
            total=Coalesce(Sum("quantidade"), 0)
        )["total"]

        return int(total or 0)


    def pode_adicionar_para_usuario(self, usuario, quantidade_desejada: int) -> tuple[bool, str]:
        limite = self.maximo_por_usuario or 0

        if limite == 0:
            return True, ""

        ja_solicitada = self.quantidade_ja_solicitada_por_usuario(usuario)
        no_carrinho = self.quantidade_no_carrinho_aberto(usuario)
        total_apos_acao = ja_solicitada + no_carrinho + int(quantidade_desejada or 0)

        if total_apos_acao > limite:
            restante = max(limite - ja_solicitada - no_carrinho, 0)

            if restante <= 0:
                return False, f"Você já atingiu o limite máximo de {limite} unidade(s) para este produto."

            return False, (
                f"Você pode adicionar no máximo mais {restante} unidade(s) deste produto. "
                f"Limite por usuário: {limite}."
            )

        return True, ""


    def pode_finalizar_no_checkout(self, usuario, quantidade_no_carrinho: int) -> tuple[bool, str]:
        limite = self.maximo_por_usuario or 0

        if limite == 0:
            return True, ""

        ja_solicitada = self.quantidade_ja_solicitada_por_usuario(usuario)
        total_final = ja_solicitada + int(quantidade_no_carrinho or 0)

        if total_final > limite:
            restante = max(limite - ja_solicitada, 0)

            if restante <= 0:
                return False, f"Você já atingiu o limite máximo de {limite} unidade(s) para este produto."

            return False, (
                f"Você pode finalizar no máximo mais {restante} unidade(s) deste produto. "
                f"Limite por usuário: {limite}."
            )

        return True, ""
    
    def quantidade_maxima_no_carrinho_para_usuario(self, usuario, quantidade_atual_item: int = 0) -> int:
        """
        Retorna o máximo que o usuário pode deixar neste item do carrinho,
        considerando ao mesmo tempo:
        - estoque disponível
        - o que já está reservado no próprio item
        - limite máximo por usuário

        quantidade_atual_item = quantidade já existente neste item específico do carrinho.
        """
        quantidade_atual_item = int(quantidade_atual_item or 0)

        # Estoque disponível para este usuário editar este item:
        # devolve temporariamente o que já está reservado no próprio item
        max_por_estoque = max((self.estoque_disponivel or 0) + quantidade_atual_item, 0)

        limite = self.maximo_por_usuario or 0
        if limite == 0:
            return max_por_estoque

        ja_solicitada = self.quantidade_ja_solicitada_por_usuario(usuario)
        no_carrinho = self.quantidade_no_carrinho_aberto(usuario)

        # remove da conta o item atual, porque ele já está dentro de no_carrinho
        no_carrinho_sem_item_atual = max(no_carrinho - quantidade_atual_item, 0)

        max_por_limite = max(limite - ja_solicitada - no_carrinho_sem_item_atual, 0)

        return max(min(max_por_estoque, max_por_limite), 0)


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
        if not self.imagem:
            return super().save(*args, **kwargs)

        original_name = self.imagem.name or ""
        if original_name.lower().endswith(".webp"):
            return super().save(*args, **kwargs)

        if self.pk:
            old = type(self).objects.filter(pk=self.pk).only("imagem").first()
            if old and old.imagem and old.imagem.name == self.imagem.name:
                return super().save(*args, **kwargs)

        self.imagem.open("rb")
        img = Image.open(self.imagem)

        img = ImageOps.exif_transpose(img)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        max_w, max_h = 1600, 1600
        img.thumbnail((max_w, max_h))

        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=85, method=6)
        buffer.seek(0)

        base, _ext = os.path.splitext(os.path.basename(self.imagem.name))
        new_name = f"{base}.webp"
        self.imagem.save(new_name, ContentFile(buffer.read()), save=False)

        return super().save(*args, **kwargs)


class Carrinho(models.Model):
    class Status(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        FECHADO = "FECHADO", "Fechado"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTO)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario"],
                condition=models.Q(status="ABERTO"),
                name="unique_open_cart_per_user",
            )
        ]

    def __str__(self):
        return f"Carrinho {self.id} - {self.usuario} ({self.status})"

    @property
    def total_itens(self) -> int:
        agg = self.itens.aggregate(q=Coalesce(Sum("quantidade"), 0))
        return int(agg["q"] or 0)

    @property
    def total_valor(self) -> Decimal:
        agg = self.itens.aggregate(
            total=Coalesce(
                Sum(
                    F("quantidade") * F("preco_unitario"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        return (agg["total"] or Decimal("0.00")).quantize(Decimal("0.01"))


class CarrinhoItem(models.Model):
    carrinho = models.ForeignKey("Carrinho", on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("Produto", on_delete=models.PROTECT, related_name="itens_carrinho")
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("carrinho", "produto")

    def save(self, *args, **kwargs):
        if not self.preco_unitario or self.preco_unitario <= 0:
            self.preco_unitario = self.produto.valor_venda
        super().save(*args, **kwargs)

    @property
    def subtotal(self) -> Decimal:
        preco = self.preco_unitario or Decimal("0.00")
        qtd = self.quantidade or 0
        return (preco * Decimal(qtd)).quantize(Decimal("0.01"))

    @property
    def expira_em(self):
        if not self.criado_em:
            return None
        return self.criado_em + timedelta(hours=RESERVA_HORAS)

    @property
    def expirado(self):
        expira = self.expira_em
        return bool(expira and timezone.now() >= expira)


class FormaPagamento(models.Model):
    class Codigo(models.TextChoices):
        PIX = "PIX", "Pix"
        DINHEIRO = "DINHEIRO", "Dinheiro em espécie"
        VALE = "VALE", "Vale no pagamento"

    codigo = models.CharField(max_length=20, choices=Codigo.choices)
    ativa = models.BooleanField(default=True)

    # Pix
    pix_chave = models.CharField(max_length=255, blank=True, default="")
    pix_nome = models.CharField(max_length=255, blank=True, default="")
    pix_cidade = models.CharField(max_length=255, blank=True, default="")
    pix_payload = models.TextField(blank=True, default="")

    def clean(self):
        super().clean()

        if self.codigo == self.Codigo.PIX and self.ativa:
            qs = FormaPagamento.objects.filter(
                codigo=self.Codigo.PIX,
                ativa=True
            ).exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    "ativa": "Já existe um Pix ativo. Desative o atual antes de ativar outro."
                })

        if self.codigo == self.Codigo.PIX:
            if not self.pix_chave:
                raise ValidationError({"pix_chave": "Informe a chave Pix."})
            if not self.pix_nome:
                raise ValidationError({"pix_nome": "Informe o nome do recebedor."})
            if not self.pix_cidade:
                raise ValidationError({"pix_cidade": "Informe a cidade."})
        else:
            self.pix_chave = ""
            self.pix_nome = ""
            self.pix_cidade = ""
            self.pix_payload = ""

    def __str__(self):
        return self.get_codigo_display()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                condition=Q(codigo="PIX", ativa=True),
                name="unique_pix_ativo",
            )
        ]


class RegraParcelamentoVale(models.Model):
    """
    Mantém compatibilidade com seu admin.py e centraliza as regras do VALE.
    Exemplo de regra:
      - de 0 a 200: até 1x
      - de 200.01 a 500: até 2x
      - de 500.01 a 1000: até 3x
    """
    minimo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    maximo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_parcelas = models.PositiveIntegerField(default=1)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["minimo"]

    def __str__(self):
        mx = "∞" if self.maximo is None else f"{self.maximo}"
        return f"R$ {self.minimo} a {mx} → até {self.max_parcelas}x"

    def clean(self):
        super().clean()
        if self.maximo is not None and self.maximo < self.minimo:
            raise ValidationError("O valor máximo não pode ser menor que o mínimo.")

class Venda(models.Model):

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        APROVADA = "APROVADA", "Aprovada"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        CANCELADA = "CANCELADA", "Cancelada"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vendas"
    )

    forma_pagamento = models.ForeignKey(
        "FormaPagamento",
        on_delete=models.PROTECT
    )

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parcelas = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE
    )

    observacao = models.TextField(blank=True)

    comprovante_pix = models.FileField(
        upload_to="comprovantes/pix/",
        blank=True,
        null=True
    )

    comprovante_vale = models.FileField(
        upload_to="comprovantes/vale/",
        blank=True,
        null=True
    )
    minuta = models.CharField(null=True, blank=True, verbose_name="Minuta de envio")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def recalcular_total(self):
        total = self.itens.aggregate(
            total=Coalesce(Sum("subtotal"), Decimal("0.00"))
        )["total"] or Decimal("0.00")

        self.total = total.quantize(Decimal("0.01"))
        self.save(update_fields=["total"])
    
    def repor_estoque(self):
        for item in self.itens.select_related("produto").all():
            produto = item.produto
            produto.quantidade += item.quantidade
            produto.save(update_fields=["quantidade"])
    
    def baixar_estoque(self):
        for item in self.itens.select_related("produto").all():
            produto = item.produto

            if item.quantidade > produto.quantidade:
                raise ValidationError(
                    f"Estoque insuficiente para o produto '{produto.nome}'. "
                    f"Disponível: {produto.quantidade}. Solicitado: {item.quantidade}."
                )

            produto.quantidade -= item.quantidade
            produto.save(update_fields=["quantidade"])

    def clean(self):
        super().clean()

        if (
            self.status == self.Status.APROVADA
            and self.forma_pagamento.codigo == "VALE"
            and not self.comprovante_vale
        ):
            raise ValidationError({
                "comprovante_vale": "Para aprovar uma venda em VALE, anexe o comprovante primeiro."
            })

        if (
            self.status == self.Status.APROVADA
            and self.forma_pagamento.codigo == "PIX"
            and not self.comprovante_pix
        ):
            raise ValidationError({
                "comprovante_pix": "Para aprovar uma venda Pix, o comprador deve anexar o comprovante primeiro."
            })

    def save(self, *args, **kwargs):
        self.full_clean()

        status_anterior = None
        if self.pk:
            status_anterior = Venda.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # se mudou para CANCELADA → devolve estoque
        if status_anterior != self.Status.CANCELADA and self.status == self.Status.CANCELADA:
            self.repor_estoque()

    def __str__(self):
        return f"Venda #{self.id}"


def validar_comprovante_pix(arquivo):
    if not arquivo:
        return

    max_size = 5 * 1024 * 1024
    if arquivo.size > max_size:
        raise ValidationError("O arquivo é muito grande. Máximo permitido: 5MB.")

    nome = (arquivo.name or "").lower()
    ext_ok = (".png", ".jpg", ".jpeg", ".pdf")
    if not any(nome.endswith(ext) for ext in ext_ok):
        raise ValidationError("Formato inválido. Envie PNG, JPG, JPEG ou PDF.")

    content_type = getattr(arquivo, "content_type", "")
    allowed_types = ("image/png", "image/jpeg", "application/pdf")
    if content_type and content_type not in allowed_types:
        raise ValidationError("Tipo de arquivo inválido. Envie imagem (PNG/JPG) ou PDF.")


class Pagamento(models.Model):
    venda = models.OneToOneField(Venda, on_delete=models.CASCADE, related_name="pagamento")
    tipo = models.ForeignKey(FormaPagamento, on_delete=models.PROTECT)
    parcelas = models.PositiveIntegerField(default=1)
    comprovante_pix = models.FileField(
        upload_to="comprovantes_pix/",
        blank=True,
        null=True,
        validators=[validar_comprovante_pix],
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pagamento {self.id} - {self.venda_id} - {self.tipo.codigo}"


class VendaItem(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="itens_venda"
    )
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), editable=False)

    def save(self, *args, **kwargs):
        if self.produto_id and (not self.preco_unitario or self.preco_unitario <= 0):
            self.preco_unitario = self.produto.valor_venda

        self.subtotal = (self.preco_unitario * self.quantidade).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.produto} x{self.quantidade}"

class Favorito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favoritos"
    )

    produto = models.ForeignKey(
        "Produto",
        on_delete=models.CASCADE,
        related_name="favoritado_por"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "produto")

    def __str__(self):
        return f"{self.usuario} ❤️ {self.produto}"