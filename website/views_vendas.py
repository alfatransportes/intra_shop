from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .models import Venda


@login_required
def minhas_compras(request):
    qs = (
        Venda.objects
        .filter(usuario=request.user)
        .select_related("forma_pagamento")
        .order_by("-id")  # ou "-criado_em"
    )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "website/minhas_compras.html", {"page_obj": page_obj})


@login_required
def minha_compra_detalhe(request, pk):
    # pega a venda sem filtrar pelo usuário (pra poder validar e dar mensagem)
    venda = get_object_or_404(
        Venda.objects.select_related("forma_pagamento").prefetch_related("itens__produto"),
        pk=pk,
    )

    # se não pertence ao usuário -> mensagem + redirect
    if venda.usuario_id != request.user.id:
        messages.error(request, "Você não tem permissão para acessar essa compra.")
        return redirect("index")

    return render(request, "website/minha_compra_detalhe.html", {"venda": venda})
