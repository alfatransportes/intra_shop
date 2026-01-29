# website/views_carrinho.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import CarrinhoItem, FormaPagamento, Produto
from .services.carrinho import get_carrinho_aberto


@login_required
def carrinho_detail(request):
    carrinho = get_carrinho_aberto(request.user)
    carrinho = (
        carrinho.__class__.objects
        .prefetch_related("itens__produto", "itens__produto__imagens")
        .get(pk=carrinho.pk)
    )

    formas_pagamento = FormaPagamento.objects.filter(ativa=True).order_by("codigo")

    return render(
        request,
        "website/carrinho.html",
        {"carrinho": carrinho, "formas_pagamento": formas_pagamento},
    )



@login_required
@transaction.atomic
def carrinho_add(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    carrinho = get_carrinho_aberto(request.user)

    try:
        item = (
            CarrinhoItem.objects
            .select_for_update()
            .get(carrinho=carrinho, produto=produto)
        )
        nova_qtd = item.quantidade + 1

    except CarrinhoItem.DoesNotExist:
        nova_qtd = 1
        item = CarrinhoItem(
            carrinho=carrinho,
            produto=produto,
            quantidade=0,
            preco_unitario=produto.valor_venda,
        )

    if nova_qtd > produto.quantidade:
        messages.error(
            request,
            "Quantidade solicitada maior que o estoque disponível."
        )
        return redirect("detalhe_produto", pk=produto.pk)

    item.quantidade = nova_qtd
    item.preco_unitario = produto.valor_venda
    item.save()

    messages.success(request, "Produto adicionado ao carrinho.")
    return redirect("carrinho_detail")



@login_required
@transaction.atomic
def carrinho_update(request, item_id):
    item = get_object_or_404(
        CarrinhoItem,
        pk=item_id,
        carrinho__usuario=request.user,
        carrinho__status="ABERTO",
    )

    try:
        qtd = int(request.POST.get("quantidade", item.quantidade))
    except ValueError:
        qtd = item.quantidade

    if qtd <= 0:
        item.delete()
        messages.info(request, "Item removido do carrinho.")
        return redirect("carrinho_detail")

    if qtd > item.produto.quantidade:
        messages.error(request, "Quantidade maior que o estoque disponível.")
        return redirect("carrinho_detail")

    item.quantidade = qtd
    item.preco_unitario = item.produto.valor_venda
    item.save()

    messages.success(request, "Carrinho atualizado.")
    return redirect("carrinho_detail")


@login_required
def carrinho_remove(request, item_id):
    item = get_object_or_404(CarrinhoItem, pk=item_id, carrinho__usuario=request.user, carrinho__status="ABERTO")
    item.delete()
    messages.info(request, "Item removido do carrinho.")
    return redirect("carrinho_detail")
