# website/views_carrinho.py
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CheckoutForm
from .models import CarrinhoItem, FormaPagamento, Produto
from .services.carrinho import get_carrinho_aberto


@login_required
def carrinho_detail(request):
    carrinho_aberto = get_carrinho_aberto(request.user)

    carrinho = (
        carrinho_aberto.__class__.objects
        .prefetch_related("itens__produto", "itens__produto__imagens")
        .get(pk=carrinho_aberto.pk)
    )

    # calcula máximo permitido por item no carrinho
    for item in carrinho.itens.all():
        item.maximo_permitido = item.produto.quantidade_maxima_no_carrinho_para_usuario(
            request.user,
            item.quantidade
        )

    # total para montar opções de parcelamento (VALE)
    total = getattr(carrinho, "total_valor", None)
    if total is None:
        total = Decimal("0.00")

    form = CheckoutForm(total=total)
    formas_pagamento = FormaPagamento.objects.filter(ativa=True).order_by("codigo")

    return render(
        request,
        "website/carrinho.html",
        {
            "carrinho": carrinho,
            "form": form,
            "formas_pagamento": formas_pagamento,
        },
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
        qtd_atual = item.quantidade
    except CarrinhoItem.DoesNotExist:
        item = CarrinhoItem(
            carrinho=carrinho,
            produto=produto,
            quantidade=0,
            preco_unitario=produto.valor_venda,
        )
        nova_qtd = 1
        qtd_atual = 0

    # valida limite por usuário
    permitido, erro = produto.pode_adicionar_para_usuario(request.user, 1)
    if not permitido:
        messages.error(request, erro)
        return redirect("detalhe_produto", pk=produto.pk)

    # disponível real + o que já é seu
    disponivel_para_voce = produto.estoque_disponivel + qtd_atual

    if nova_qtd > disponivel_para_voce:
        messages.error(request, "Quantidade solicitada maior que o estoque disponível.")
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

    disponivel_para_voce = item.produto.estoque_disponivel + item.quantidade

    if qtd > disponivel_para_voce:
        messages.error(request, "Quantidade maior que o estoque disponível.")
        return redirect("carrinho_detail")

    item.quantidade = qtd
    item.preco_unitario = item.produto.valor_venda
    item.save()

    messages.success(request, "Carrinho atualizado.")
    return redirect("carrinho_detail")


@login_required
def carrinho_remove(request, item_id):
    item = get_object_or_404(
        CarrinhoItem,
        pk=item_id,
        carrinho__usuario=request.user,
        carrinho__status="ABERTO",
    )
    item.delete()
    messages.info(request, "Item removido do carrinho.")
    return redirect("carrinho_detail")