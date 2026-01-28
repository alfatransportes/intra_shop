# website/views.py
from django.shortcuts import get_object_or_404, render

from .models import Produto, Tipo


def index(request):
    tipo_id = request.GET.get("tipo")  # /?tipo=1

    produtos = (
        Produto.objects
        .prefetch_related("imagens")
    )

    if tipo_id:
        produtos = produtos.filter(tipo_prod_id=tipo_id)

    tipo_produtos = Tipo.objects.all()

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
