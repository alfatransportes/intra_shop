# website/views.py
# website/views.py
from django.db.models import F, IntegerField, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from .models import Produto, Tipo


def index(request):
    tipo_id = request.GET.get("tipo")

    produtos = (
        Produto.objects
        .prefetch_related("imagens")
        .annotate(
            reservado=Coalesce(
                Sum(
                    "itens_carrinho__quantidade",
                    filter=Q(itens_carrinho__carrinho__status="ABERTO"),
                ),
                0,
                output_field=IntegerField(),
            ),
            estoque_calc=F("quantidade") - F("reservado"),
        )
        .filter(estoque_calc__gt=0)
    )

    if tipo_id and tipo_id.isdigit():
        produtos = produtos.filter(tipo_prod_id=int(tipo_id))

    tipo_produtos = Tipo.objects.all().order_by("nome")

    return render(
        request,
        "website/index.html",
        {
            "produtos": produtos,
            "tipo_produtos": tipo_produtos,
            "tipo_selecionado": tipo_id,
        }
    )


def detalhe_produto(request, pk):
    produto = (
        Produto.objects
        .prefetch_related("imagens")
        .get(pk=pk)
    )
    return render(request, "website/detalhes_produto.html", {"produto": produto})
