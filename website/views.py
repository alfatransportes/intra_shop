# website/views.py
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import RESERVA_HORAS, ConfigWebsite, Favorito, Produto, Tipo


def index(request):
    busca = (request.GET.get("q") or "").strip()
    tipo_id = (request.GET.get("categoria") or "").strip()
    ordenar = (request.GET.get("ordenar") or "").strip()

    produtos_qs = (
        Produto.objects
        .prefetch_related("imagens", "variacoes")
        .filter(ativo=True)
    )

    if busca:
        produtos_qs = produtos_qs.filter(
            Q(nome__icontains=busca) | Q(descricao__icontains=busca)
        )

    if tipo_id.isdigit():
        produtos_qs = produtos_qs.filter(tipo_prod_id=int(tipo_id))

    produtos = [p for p in produtos_qs if p.estoque_disponivel > 0]

    if ordenar == "preco":
        produtos.sort(key=lambda p: (p.valor_venda, -p.id))
    elif ordenar == "preco_desc":
        produtos.sort(key=lambda p: (-p.valor_venda, -p.id))
    elif ordenar == "nome":
        produtos.sort(key=lambda p: p.nome.lower())
    else:
        produtos.sort(key=lambda p: -p.id)

    paginator = Paginator(produtos, 12)
    page_obj = paginator.get_page(request.GET.get("page") or "1")

    categorias = Tipo.objects.all().order_by("nome")
    filtros_ativos = bool(busca or tipo_id or ordenar)

    config_ativa = (
        ConfigWebsite.objects
        .prefetch_related("banners")
        .filter(active=True)
        .first()
    )

    banners = config_ativa.banners.filter(ativo=True).order_by("ordem", "id") if config_ativa else []

    return render(
        request,
        "website/index.html",
        {
            "categorias": categorias,
            "busca": busca,
            "categoria": tipo_id,
            "ordenar": ordenar,
            "filtros_ativos": filtros_ativos,
            "page_obj": page_obj,
            "produtos": page_obj.object_list,
            "total_produtos": paginator.count,
            "config_ativa": config_ativa,
            "banners": banners,
        },
    )


def detalhe_produto(request, pk):
    produto = get_object_or_404(
        Produto.objects.prefetch_related(
            "imagens",
            "variacoes",
        ).select_related(
            "tipo_prod",
            "unidade_prod",
            "nivel_ava_prod",
        ),
        pk=pk,
        ativo=True,
    )

    economia = Decimal("0.00")
    try:
        if produto.valor_nota and produto.valor_venda and produto.valor_nota > produto.valor_venda:
            economia = (produto.valor_nota - produto.valor_venda).quantize(Decimal("0.01"))
    except Exception:
        economia = Decimal("0.00")

    favoritado = False
    if request.user.is_authenticated:
        favoritado = Favorito.objects.filter(
            usuario=request.user,
            produto=produto
        ).exists()

    relacionados = (
        Produto.objects
        .filter(tipo_prod=produto.tipo_prod, ativo=True)
        .exclude(pk=produto.pk)
        .prefetch_related("imagens")
        .order_by("?")[:4]
    )

    restante_para_usuario = None
    if request.user.is_authenticated:
        limite = produto.maximo_por_usuario or 0
        if limite > 0:
            ja_solicitada = produto.quantidade_ja_solicitada_por_usuario(request.user)
            no_carrinho = produto.quantidade_no_carrinho_aberto(request.user)
            restante_para_usuario = max(limite - ja_solicitada - no_carrinho, 0)

    return render(
        request,
        "website/detalhes_produto.html",
        {
            "produto": produto,
            "economia": economia,
            "favoritado": favoritado,
            "relacionados": relacionados,
            "restante_para_usuario": restante_para_usuario,
            "variacoes_disponiveis": produto.variacoes_disponiveis if produto.usa_variacoes else [],
        },
    )


@login_required
def favorito_toggle(request, produto_id):

    produto = get_object_or_404(Produto, id=produto_id)

    favorito, created = Favorito.objects.get_or_create(
        usuario=request.user,
        produto=produto
    )

    if not created:
        favorito.delete()

    return redirect(request.META.get("HTTP_REFERER", "index"))


@login_required
def meus_favoritos(request):

    favoritos = (
        Favorito.objects
        .filter(usuario=request.user)
        .select_related("produto")
        .prefetch_related("produto__imagens")
        .order_by("-criado_em")
    )

    return render(
        request,
        "website/favoritos.html",
        {
            "favoritos": favoritos
        },
    )
