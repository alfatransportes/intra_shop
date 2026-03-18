# website/views.py
from datetime import timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import F, IntegerField, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import RESERVA_HORAS, Produto, Tipo


def index(request):
    # parâmetros
    busca = (request.GET.get("q") or "").strip()
    tipo_id = (request.GET.get("categoria") or "").strip()
    ordenar = (request.GET.get("ordenar") or "").strip()

    # paginação
    page_number = request.GET.get("page") or "1"
    try:
        page_number_int = int(page_number)
    except ValueError:
        page_number_int = 1

    limite = timezone.now() - timedelta(hours=RESERVA_HORAS)

    produtos_qs = (
        Produto.objects
        .prefetch_related("imagens")
        .annotate(
            reservado=Coalesce(
                Sum(
                    "itens_carrinho__quantidade",
                    filter=Q(
                        itens_carrinho__carrinho__status="ABERTO",
                        itens_carrinho__atualizado_em__gte=limite,
                    ),
                ),
                0,
                output_field=IntegerField(),
            ),
            estoque_calc=F("quantidade") - F("reservado"),
        )
        .filter(estoque_calc__gt=0)
    )

    # busca
    if busca:
        produtos_qs = produtos_qs.filter(
            Q(nome__icontains=busca) | Q(descricao__icontains=busca)
        )

    # categoria
    if tipo_id.isdigit():
        produtos_qs = produtos_qs.filter(tipo_prod_id=int(tipo_id))

    # ordenação
    if ordenar == "preco":
        produtos_qs = produtos_qs.order_by("valor_venda", "-id")
    elif ordenar == "preco_desc":
        produtos_qs = produtos_qs.order_by("-valor_venda", "-id")
    elif ordenar == "nome":
        produtos_qs = produtos_qs.order_by("nome")
    else:
        produtos_qs = produtos_qs.order_by("-id")

    categorias = Tipo.objects.all().order_by("nome")

    paginator = Paginator(produtos_qs, 12)  # 12 por página
    page_obj = paginator.get_page(page_number_int)

    filtros_ativos = bool(busca or tipo_id or ordenar)

    return render(
        request,
        "website/index.html",
        {
            "categorias": categorias,
            "busca": busca,
            "categoria": tipo_id,
            "ordenar": ordenar,
            "filtros_ativos": filtros_ativos,
            "page_obj": page_obj,        # paginado
            "produtos": page_obj.object_list,  # lista atual
            "total_produtos": paginator.count,
        },
    )


def detalhe_produto(request, pk):
    produto = get_object_or_404(
        Produto.objects.prefetch_related("imagens", "tipo_prod", "unidade_prod", "nivel_ava_prod"),
        pk=pk,
    )

    # cálculo seguro de economia (evita matemática no template)
    economia = Decimal("0.00")
    try:
        if produto.valor_nota and produto.valor_venda and produto.valor_nota > produto.valor_venda:
            economia = (produto.valor_nota - produto.valor_venda).quantize(Decimal("0.01"))
    except Exception:
        economia = Decimal("0.00")

    return render(
        request,
        "website/detalhes_produto.html",
        {
            "produto": produto,
            "economia": economia,
        },
    )