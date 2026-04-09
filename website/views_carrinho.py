from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CheckoutForm
from .models import CarrinhoItem, FormaPagamento, Produto, ProdutoVariacao
from .services.carrinho import get_carrinho_aberto


@login_required
def carrinho_detail(request):
    carrinho_aberto = get_carrinho_aberto(request.user)

    carrinho = (
        carrinho_aberto.__class__.objects
        .prefetch_related("itens__produto", "itens__produto__imagens", "itens__variacao")
        .get(pk=carrinho_aberto.pk)
    )

    for item in carrinho.itens.all():
        if item.variacao_id:
            item.maximo_permitido = max((item.variacao.quantidade or 0), 0)
        else:
            item.maximo_permitido = item.produto.quantidade_maxima_no_carrinho_para_usuario(
                request.user,
                item.quantidade
            )

    total = getattr(carrinho, "total_valor", None) or Decimal("0.00")
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
    produto = get_object_or_404(Produto, pk=pk, ativo=True)
    carrinho = get_carrinho_aberto(request.user)

    quantidade = 1
    try:
        quantidade = int(request.POST.get("quantidade") or 1)
    except (TypeError, ValueError):
        quantidade = 1

    if quantidade <= 0:
        messages.error(request, "Informe uma quantidade válida.")
        return redirect("detalhe_produto", pk=produto.pk)

    variacao = None
    variacao_id = request.POST.get("variacao_id")

    if produto.usa_variacoes:
        if not variacao_id:
            messages.error(request, "Selecione o tamanho antes de adicionar ao carrinho.")
            return redirect("detalhe_produto", pk=produto.pk)

        variacao = get_object_or_404(
            ProdutoVariacao.objects.select_for_update(),
            pk=variacao_id,
            produto=produto,
            ativo=True,
        )

        try:
            item = CarrinhoItem.objects.select_for_update().get(
                carrinho=carrinho,
                produto=produto,
                variacao=variacao,
            )
            qtd_atual = item.quantidade
        except CarrinhoItem.DoesNotExist:
            item = CarrinhoItem(
                carrinho=carrinho,
                produto=produto,
                variacao=variacao,
                quantidade=0,
                preco_unitario=produto.valor_venda,
            )
            qtd_atual = 0

        nova_qtd = qtd_atual + quantidade

        if nova_qtd > (variacao.quantidade or 0):
            messages.error(request, "Quantidade solicitada maior que o estoque disponível dessa variação.")
            return redirect("detalhe_produto", pk=produto.pk)

    else:
        permitido, erro = produto.pode_adicionar_para_usuario(request.user, quantidade)
        if not permitido:
            messages.error(request, erro)
            return redirect("detalhe_produto", pk=produto.pk)

        try:
            item = CarrinhoItem.objects.select_for_update().get(
                carrinho=carrinho,
                produto=produto,
                variacao__isnull=True,
            )
            qtd_atual = item.quantidade
        except CarrinhoItem.DoesNotExist:
            item = CarrinhoItem(
                carrinho=carrinho,
                produto=produto,
                variacao=None,
                quantidade=0,
                preco_unitario=produto.valor_venda,
            )
            qtd_atual = 0

        nova_qtd = qtd_atual + quantidade
        disponivel_para_voce = produto.estoque_disponivel + qtd_atual

        if nova_qtd > disponivel_para_voce:
            messages.error(request, "Quantidade solicitada maior que o estoque disponível.")
            return redirect("detalhe_produto", pk=produto.pk)

    item.quantidade = nova_qtd
    item.preco_unitario = produto.valor_venda
    item.save()

    acao = request.POST.get("acao")
    messages.success(request, "Produto adicionado ao carrinho.")

    if acao == "comprar":
        return redirect("carrinho_detail")
    return redirect("carrinho_detail")


@login_required
@transaction.atomic
def carrinho_update(request, item_id):
    item = get_object_or_404(
        CarrinhoItem.objects.select_related("produto", "variacao"),
        pk=item_id,
        carrinho__usuario=request.user,
        carrinho__status="ABERTO",
    )

    try:
        qtd = int(request.POST.get("quantidade", item.quantidade))
    except (TypeError, ValueError):
        qtd = item.quantidade

    if qtd <= 0:
        item.delete()
        messages.info(request, "Item removido do carrinho.")
        return redirect("carrinho_detail")

    if item.variacao_id:
        if qtd > (item.variacao.quantidade or 0):
            messages.error(request, "Quantidade maior que o estoque disponível dessa variação.")
            return redirect("carrinho_detail")
    else:
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