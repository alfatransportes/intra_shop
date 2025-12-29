# website/views.py
from django.shortcuts import get_object_or_404, render

from .models import Produto


def index(request):
    produtos = (
        Produto.objects
        .prefetch_related("imagens")  # ok
        # NÃO anote estoque_disponivel aqui
    )
    return render(request, "website/index.html", {"produtos": produtos})


def detalhe_produto(request, pk):
    produto = (
        Produto.objects
        .prefetch_related("imagens")
        .get(pk=pk)
    )
    return render(request, "website/detalhes_produto.html", {"produto": produto})
