import os
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from PIL import Image, ImageOps

RESERVA_HORAS = 4


def upload_to(instance, filename):
    base, _ext = os.path.splitext(filename)
    return f"produtos/{base}.webp"


class ConfigWebsite(models.Model):
    titulo = models.CharField(max_length=50, verbose_name="Título da Configuração")
    cor_destaque = models.CharField(max_length=7, default="#DE1E3E", verbose_name="Cor do título")
    logo = models.ImageField(upload_to="imagensConfiguracaoWebsite/", verbose_name="Logotipo")
    favicon = models.ImageField(upload_to="imagensConfiguracaoWebsite/", verbose_name="Favicon")
    image_auth = models.ImageField(upload_to="imagensConfiguracaoWebsite/", blank=True, null=True, verbose_name="Imagem de Autenticação")
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
        if self.active and ConfigWebsite.objects.filter(active=True).exclude(pk=self.pk).exists():
            raise ValidationError("Já existe uma configuração ativa. Desative a outra antes de ativar esta.")


class BannerConfigWebsite(models.Model):
    config_website = models.ForeignKey(ConfigWebsite, on_delete=models.CASCADE, related_name="banners")
    titulo = models.CharField(max_length=120, blank=True, null=True)
    subtitulo = models.CharField(max_length=255, blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    banner = models.ImageField(upload_to="imagensBannersConfiguracaoWebsite/")
    ordem = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
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
            total_banners = BannerConfigWebsite.objects.filter(config_website=self.config_website).exclude(pk=self.pk).count()
            if total_banners >= 10:
                raise ValidationError("Cada configuração pode ter no máximo 10 banners no carrossel.")

    def _imagem_foi_alterada(self):
        if not self.pk:
            return True
        antigo = type(self).objects.filter(pk=self.pk).only("banner").first()
        if not antigo:
            return True
        return (antigo.banner.name if antigo.banner else None) != (self.banner.name if self.banner else None)

    def _gerar_banner_webp(self):
        self.banner.seek(0)
        with Image.open(self.banner) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
            img.thumbnail((1920, 420), Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="WEBP", quality=85, method=6, optimize=True)
            buffer.seek(0)
        nome_base, _ = os.path.splitext(os.path.basename(self.banner.name))
        return f"{nome_base}_{uuid.uuid4().hex[:10]}.webp", ContentFile(buffer.read())

    def save(self, *args, **kwargs):
        if self.banner and self._imagem_foi_alterada():
            nome, arquivo = self._gerar_banner_webp()
            self.banner.save(nome, arquivo, save=False)
        super().save(*args, **kwargs)


class Unidade(models.Model):
    codigo = models.IntegerField(blank=True, null=True)
    nome = models.CharField(max_length=255)

    class Meta:
        ordering = ["codigo", "nome"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}" if self.codigo else self.nome


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
    unidade_prod = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="produtos")
    tipo_prod = models.ForeignKey(Tipo, on_delete=models.PROTECT, related_name="produtos")
    nivel_ava_prod = models.ForeignKey(NivelAvaria, on_delete=models.PROTECT, related_name="produtos")
    num_controle = models.CharField(max_length=255, null=True, blank=True)
    nome = models.CharField(max_length=255)
    usa_variacoes = models.BooleanField(default=False)
    quantidade = models.PositiveIntegerField(default=1)
    maximo_por_usuario = models.PositiveIntegerField(default=0)
    valor_nota = models.DecimalField(max_digits=10, decimal_places=2)
    porcen_desconto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
    )
    valor_venda = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    descricao = models.TextField()
    ativo = models.BooleanField(default=False)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.id} - {self.nome}"

    def save(self, *args, **kwargs):
        desconto = (self.porcen_desconto or Decimal("0")) / Decimal("100")
        self.valor_venda = (self.valor_nota * (Decimal("1") - desconto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if self.usa_variacoes:
            self.quantidade = 0
        super().save(*args, **kwargs)
        pode_ativar, _ = self.pode_ativar()
        if self.ativo and not pode_ativar:
            self.ativo = False
            super().save(update_fields=["ativo"])

    @property
    def estoque_total_variacoes(self) -> int:
        return int(self.variacoes.filter(ativo=True).aggregate(total=Coalesce(Sum("quantidade"), 0))["total"] or 0)

    @property
    def estoque_disponivel(self) -> int:
        limite = timezone.now() - timedelta(hours=RESERVA_HORAS)
        reservado = self.itens_carrinho.filter(carrinho__status="ABERTO", atualizado_em__gte=limite).aggregate(
            q=Coalesce(Sum("quantidade"), 0)
        )["q"]
        estoque_base = self.estoque_total_variacoes if self.usa_variacoes else int(self.quantidade or 0)
        return max(estoque_base - int(reservado or 0), 0)

    @property
    def tem_variacoes_ativas_com_estoque(self) -> bool:
        return self.variacoes.filter(ativo=True, quantidade__gt=0).exists()

    @property
    def variacoes_disponiveis(self):
        return self.variacoes.filter(ativo=True, quantidade__gt=0).order_by("categoria", "genero", "faixa_etaria", "tamanho", "id")

    def pode_ativar(self):
        if not self.imagens.exists():
            return False, "Para ativar o produto, adicione ao menos uma imagem."
        if self.usa_variacoes:
            if not self.tem_variacoes_ativas_com_estoque:
                return False, "Para ativar um produto com variações, cadastre ao menos uma variação ativa com estoque."
            return True, ""
        if int(self.quantidade or 0) <= 0:
            return False, "Para ativar o produto, informe uma quantidade maior que zero."
        return True, ""

    def quantidade_ja_solicitada_por_usuario(self, usuario) -> int:
        if not usuario or not usuario.is_authenticated:
            return 0
        total = self.itens_venda.filter(venda__usuario=usuario).exclude(venda__status=Venda.Status.CANCELADA).aggregate(
            total=Coalesce(Sum("quantidade"), 0)
        )["total"]
        return int(total or 0)

    def quantidade_no_carrinho_aberto(self, usuario) -> int:
        if not usuario or not usuario.is_authenticated:
            return 0
        total = self.itens_carrinho.filter(carrinho__usuario=usuario, carrinho__status=Carrinho.Status.ABERTO).aggregate(
            total=Coalesce(Sum("quantidade"), 0)
        )["total"]
        return int(total or 0)

    def pode_adicionar_para_usuario(self, usuario, quantidade_desejada: int):
        limite = int(self.maximo_por_usuario or 0)
        if limite == 0:
            return True, ""
        ja_solicitada = self.quantidade_ja_solicitada_por_usuario(usuario)
        no_carrinho = self.quantidade_no_carrinho_aberto(usuario)
        total_apos_acao = ja_solicitada + no_carrinho + int(quantidade_desejada or 0)
        if total_apos_acao > limite:
            restante = max(limite - ja_solicitada - no_carrinho, 0)
            if restante <= 0:
                return False, f"Você já atingiu o limite máximo de {limite} unidade(s) para este produto."
            return False, f"Você pode adicionar no máximo mais {restante} unidade(s) deste produto. Limite por usuário: {limite}."
        return True, ""

    def pode_finalizar_no_checkout(self, usuario, quantidade_no_carrinho: int):
        limite = int(self.maximo_por_usuario or 0)
        if limite == 0:
            return True, ""
        ja_solicitada = self.quantidade_ja_solicitada_por_usuario(usuario)
        total_final = ja_solicitada + int(quantidade_no_carrinho or 0)
        if total_final > limite:
            restante = max(limite - ja_solicitada, 0)
            if restante <= 0:
                return False, f"Você já atingiu o limite máximo de {limite} unidade(s) para este produto."
            return False, f"Você pode finalizar no máximo mais {restante} unidade(s) deste produto. Limite por usuário: {limite}."
        return True, ""

    def quantidade_maxima_no_carrinho_para_usuario(self, usuario, quantidade_atual_item: int = 0) -> int:
        quantidade_atual_item = int(quantidade_atual_item or 0)
        max_por_estoque = max(int(self.estoque_disponivel or 0) + quantidade_atual_item, 0)
        limite = int(self.maximo_por_usuario or 0)
        if limite == 0:
            return max_por_estoque
        ja_solicitada = self.quantidade_ja_solicitada_por_usuario(usuario)
        no_carrinho = self.quantidade_no_carrinho_aberto(usuario)
        no_carrinho_sem_item_atual = max(no_carrinho - quantidade_atual_item, 0)
        max_por_limite = max(limite - ja_solicitada - no_carrinho_sem_item_atual, 0)
        return max(min(max_por_estoque, max_por_limite), 0)


class ProdutoImagem(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="imagens")
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
        img.thumbnail((1600, 1600))
        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=85, method=6)
        buffer.seek(0)
        base, _ext = os.path.splitext(os.path.basename(self.imagem.name))
        self.imagem.save(f"{base}.webp", ContentFile(buffer.read()), save=False)
        return super().save(*args, **kwargs)


class ProdutoVariacao(models.Model):
    class Categoria(models.TextChoices):
        CALCADO = "CALCADO", "Calçado"
        ROUPA = "ROUPA", "Roupa"
        OUTRO = "OUTRO", "Outro"

    class Genero(models.TextChoices):
        MASCULINO = "MASCULINO", "Masculino"
        FEMININO = "FEMININO", "Feminino"
        UNISSEX = "UNISSEX", "Unissex"

    class FaixaEtaria(models.TextChoices):
        ADULTO = "ADULTO", "Adulto"
        INFANTIL = "INFANTIL", "Infantil"

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="variacoes")
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.OUTRO)
    genero = models.CharField(max_length=20, choices=Genero.choices, blank=True, null=True)
    faixa_etaria = models.CharField(max_length=20, choices=FaixaEtaria.choices, blank=True, null=True)
    tamanho = models.CharField(max_length=20, blank=True, null=True)
    cor = models.CharField(max_length=50, blank=True, null=True)
    quantidade = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["categoria", "genero", "faixa_etaria", "tamanho", "cor", "id"]
        constraints = [
            models.UniqueConstraint(fields=["produto", "categoria", "genero", "faixa_etaria", "tamanho", "cor"], name="unique_produto_variacao")
        ]

    def __str__(self):
        partes = [self.produto.nome]
        if self.categoria:
            partes.append(self.get_categoria_display())
        if self.genero:
            partes.append(self.get_genero_display())
        if self.faixa_etaria:
            partes.append(self.get_faixa_etaria_display())
        if self.tamanho:
            partes.append(f"Tamanho {self.tamanho}")
        if self.cor:
            partes.append(self.cor)
        return " - ".join(partes)

    def clean(self):
        super().clean()
        self.tamanho = (self.tamanho or "").strip().upper() or None
        self.cor = (self.cor or "").strip() or None
        if self.quantidade < 0:
            raise ValidationError({"quantidade": "A quantidade não pode ser negativa."})
        if self.quantidade > 0 and not self.tamanho:
            raise ValidationError({"tamanho": "Informe o tamanho da variação."})


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
            models.UniqueConstraint(fields=["usuario"], condition=Q(status="ABERTO"), name="unique_open_cart_per_user")
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
                Sum(F("quantidade") * F("preco_unitario"), output_field=DecimalField(max_digits=12, decimal_places=2)),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        return (agg["total"] or Decimal("0.00")).quantize(Decimal("0.01"))


class CarrinhoItem(models.Model):
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="itens_carrinho")
    variacao = models.ForeignKey("ProdutoVariacao", on_delete=models.PROTECT, related_name="itens_carrinho", null=True, blank=True)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["carrinho", "produto", "variacao"], name="unique_cart_product_variation")]

    def save(self, *args, **kwargs):
        if self.produto.usa_variacoes and not self.variacao_id:
            raise ValidationError("Selecione uma variação para este produto.")
        if self.variacao_id and self.variacao.produto_id != self.produto_id:
            raise ValidationError("A variação informada não pertence ao produto.")
        if not self.preco_unitario or self.preco_unitario <= 0:
            self.preco_unitario = self.produto.valor_venda
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return ((self.preco_unitario or Decimal("0.00")) * Decimal(self.quantidade or 0)).quantize(Decimal("0.01"))

    @property
    def expira_em(self):
        return self.criado_em + timedelta(hours=RESERVA_HORAS) if self.criado_em else None

    @property
    def expirado(self):
        return bool(self.expira_em and timezone.now() >= self.expira_em)


class FormaPagamento(models.Model):
    class Codigo(models.TextChoices):
        PIX = "PIX", "Pix"
        DINHEIRO = "DINHEIRO", "Dinheiro em espécie"
        VALE = "VALE", "Vale no pagamento"

    codigo = models.CharField(max_length=20, choices=Codigo.choices)
    ativa = models.BooleanField(default=True)
    pix_chave = models.CharField(max_length=255, blank=True, default="")
    pix_nome = models.CharField(max_length=255, blank=True, default="")
    pix_cidade = models.CharField(max_length=255, blank=True, default="")
    pix_payload = models.TextField(blank=True, default="")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["codigo"], condition=Q(codigo="PIX", ativa=True), name="unique_pix_ativo")]

    def clean(self):
        super().clean()
        if self.codigo == self.Codigo.PIX and self.ativa:
            qs = FormaPagamento.objects.filter(codigo=self.Codigo.PIX, ativa=True).exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"ativa": "Já existe um Pix ativo. Desative o atual antes de ativar outro."})
        if self.codigo == self.Codigo.PIX:
            if not self.pix_chave:
                raise ValidationError({"pix_chave": "Informe a chave Pix."})
            if not self.pix_nome:
                raise ValidationError({"pix_nome": "Informe o nome do recebedor."})
            if not self.pix_cidade:
                raise ValidationError({"pix_cidade": "Informe a cidade."})
        else:
            self.pix_chave = self.pix_nome = self.pix_cidade = self.pix_payload = ""

    def __str__(self):
        return self.get_codigo_display()


class RegraParcelamentoVale(models.Model):
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

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vendas")
    forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parcelas = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    observacao = models.TextField(blank=True)
    comprovante_pix = models.FileField(upload_to="comprovantes/pix/", blank=True, null=True)
    comprovante_vale = models.FileField(upload_to="comprovantes/vale/", blank=True, null=True)
    minuta = models.CharField(null=True, blank=True, verbose_name="Minuta de envio")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Venda #{self.id}"

    @property
    def precisa_comprovante_pix(self):
        return self.forma_pagamento.codigo == FormaPagamento.Codigo.PIX and self.status == self.Status.PENDENTE and not self.comprovante_pix

    @property
    def comprovante_principal(self):
        if self.forma_pagamento.codigo == FormaPagamento.Codigo.PIX:
            return self.comprovante_pix
        if self.forma_pagamento.codigo == FormaPagamento.Codigo.VALE:
            return self.comprovante_vale
        return None

    def recalcular_total(self):
        total = self.itens.aggregate(total=Coalesce(Sum("subtotal"), Decimal("0.00")))["total"] or Decimal("0.00")
        self.total = total.quantize(Decimal("0.01"))
        self.save(update_fields=["total"])

    def repor_estoque(self):
        for item in self.itens.select_related("produto", "variacao").all():
            if item.variacao_id:
                item.variacao.quantidade += item.quantidade
                item.variacao.save(update_fields=["quantidade"])
            else:
                item.produto.quantidade += item.quantidade
                item.produto.save(update_fields=["quantidade"])

    def clean(self):
        super().clean()
        if self.status == self.Status.APROVADA and self.forma_pagamento.codigo == FormaPagamento.Codigo.VALE and not self.comprovante_vale:
            raise ValidationError({"comprovante_vale": "Para aprovar uma venda em VALE, anexe o comprovante primeiro."})
        if self.status == self.Status.APROVADA and self.forma_pagamento.codigo == FormaPagamento.Codigo.PIX and not self.comprovante_pix:
            raise ValidationError({"comprovante_pix": "Para aprovar uma venda Pix, o comprador deve anexar o comprovante primeiro."})

    def save(self, *args, **kwargs):
        self.full_clean()
        status_anterior = None
        if self.pk:
            status_anterior = Venda.objects.get(pk=self.pk).status
        super().save(*args, **kwargs)
        if status_anterior != self.Status.CANCELADA and self.status == self.Status.CANCELADA:
            self.repor_estoque()



def validar_comprovante_pix(arquivo):
    if not arquivo:
        return
    if arquivo.size > 5 * 1024 * 1024:
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
    comprovante_pix = models.FileField(upload_to="comprovantes_pix/", blank=True, null=True, validators=[validar_comprovante_pix])
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pagamento {self.id} - {self.venda_id} - {self.tipo.codigo}"


class VendaItem(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="itens_venda")
    variacao = models.ForeignKey("ProdutoVariacao", on_delete=models.PROTECT, related_name="itens_venda", null=True, blank=True)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), editable=False)

    def save(self, *args, **kwargs):
        if self.produto.usa_variacoes and not self.variacao_id:
            raise ValidationError("VendaItem de produto com variação exige uma variação.")
        if self.variacao_id and self.variacao.produto_id != self.produto_id:
            raise ValidationError("A variação informada não pertence ao produto.")
        if self.produto_id and (not self.preco_unitario or self.preco_unitario <= 0):
            self.preco_unitario = self.produto.valor_venda
        self.subtotal = (self.preco_unitario * self.quantidade).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class Favorito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favoritos")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="favoritado_por")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "produto")

    def __str__(self):
        return f"{self.usuario} ❤️ {self.produto}"
