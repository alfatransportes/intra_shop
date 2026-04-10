from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import ConfigWebsite, Favorito, Produto, Tipo
from .querysets import produtos_com_estoque_disponivel


def index(request):
    busca = (request.GET.get("q") or "").strip()
    tipo_id = (request.GET.get("categoria") or "").strip()
    ordenar = (request.GET.get("ordenar") or "").strip()

    produtos_qs = produtos_com_estoque_disponivel().filter(
        ativo=True,
        estoque_calc__gt=0,
    )

    if busca:
        produtos_qs = produtos_qs.filter(
            Q(nome__icontains=busca) | Q(descricao__icontains=busca)
        )

    if tipo_id.isdigit():
        produtos_qs = produtos_qs.filter(tipo_prod_id=int(tipo_id))

    ordenacao = {
        "preco": ("valor_venda", "-id"),
        "preco_desc": ("-valor_venda", "-id"),
        "nome": ("nome", "-id"),
    }.get(ordenar, ("-id",))

    produtos_qs = produtos_qs.order_by(*ordenacao)

    paginator = Paginator(produtos_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page") or "1")

    categorias = Tipo.objects.filter(ativo=True).order_by("nome")
    filtros_ativos = bool(busca or tipo_id or ordenar)

    config_ativa = (
        ConfigWebsite.objects
        .prefetch_related("banners")
        .filter(active=True)
        .first()
    )

    banners = (
        config_ativa.banners.filter(ativo=True).order_by("ordem", "id")
        if config_ativa else []
    )

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
        Produto.objects.prefetch_related("imagens", "variacoes").select_related(
            "tipo_prod", "unidade_prod", "nivel_ava_prod"
        ),
        pk=pk,
        ativo=True,
    )

    economia = Decimal("0.00")
    if produto.valor_nota and produto.valor_venda and produto.valor_nota > produto.valor_venda:
        economia = (produto.valor_nota - produto.valor_venda).quantize(Decimal("0.01"))

    favoritado = False
    if request.user.is_authenticated:
        favoritado = Favorito.objects.filter(usuario=request.user, produto=produto).exists()

    relacionados = (
        produtos_com_estoque_disponivel()
        .filter(tipo_prod=produto.tipo_prod, ativo=True, estoque_calc__gt=0)
        .exclude(pk=produto.pk)
        .prefetch_related("imagens")
        .order_by("?")[:4]
    )

    restante_para_usuario = None
    if request.user.is_authenticated and (produto.maximo_por_usuario or 0) > 0:
        ja_solicitada = produto.quantidade_ja_solicitada_por_usuario(request.user)
        no_carrinho = produto.quantidade_no_carrinho_aberto(request.user)
        restante_para_usuario = max((produto.maximo_por_usuario or 0) - ja_solicitada - no_carrinho, 0)

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
@require_POST
def favorito_toggle(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, ativo=True)
    favorito, created = Favorito.objects.get_or_create(usuario=request.user, produto=produto)
    if not created:
        favorito.delete()
        messages.info(request, "Produto removido dos favoritos.")
    else:
        messages.success(request, "Produto adicionado aos favoritos.")
    return redirect(request.POST.get("next") or request.META.get("HTTP_REFERER") or "index")


@login_required
def meus_favoritos(request):
    favoritos = (
        Favorito.objects.filter(usuario=request.user)
        .select_related("produto", "produto__tipo_prod")
        .prefetch_related("produto__imagens")
        .order_by("-criado_em")
    )
    return render(request, "website/favoritos.html", {"favoritos": favoritos})
