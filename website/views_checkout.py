# views_checkout.py

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from website.utils import inserir_ou_atualizar_valor

from .forms import CheckoutForm, ComprovantePixForm
from .models import FormaPagamento, Produto, Venda, VendaItem
from .services.carrinho import get_carrinho_aberto

# -----------------------
# Util
# -----------------------

def _calcular_total_carrinho(carrinho) -> Decimal:
    total = Decimal("0.00")
    for item in carrinho.itens.all():
        total += item.preco_unitario * Decimal(item.quantidade)
    return total.quantize(Decimal("0.01"))


# -----------------------
# Checkout
# -----------------------

@login_required
@transaction.atomic
def checkout(request):
    carrinho = get_carrinho_aberto(request.user)

    carrinho = (
        carrinho.__class__.objects
        .select_related("usuario")
        .prefetch_related("itens__produto")
        .get(pk=carrinho.pk)
    )

    if not carrinho.itens.exists():
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("index")

    total_preview = _calcular_total_carrinho(carrinho)

    if request.method == "POST":
        form = CheckoutForm(request.POST, total=total_preview)

        if form.is_valid():
            forma = form.cleaned_data["forma_pagamento"]
            observacao = form.cleaned_data.get("observacao", "")

            # Parcelas (apenas VALE)
            parcelas = 1
            if forma.codigo == FormaPagamento.Codigo.VALE:
                parcelas = int(form.cleaned_data.get("parcelas") or 1)

            # trava produtos
            produto_ids = list(carrinho.itens.values_list("produto_id", flat=True))
            produtos = Produto.objects.select_for_update().filter(id__in=produto_ids)
            mapa_produtos = {p.id: p for p in produtos}

            # valida estoque
            for item in carrinho.itens.all():
                produto = mapa_produtos[item.produto_id]
                if item.quantidade > produto.quantidade:
                    messages.error(request, f"Estoque insuficiente para {produto.nome}.")
                    return redirect("carrinho_detail")

            # cria venda
            venda = Venda.objects.create(
                usuario=request.user,
                forma_pagamento=forma,
                observacao=observacao,
                status=Venda.Status.PENDENTE,
                total=Decimal("0.00"),
                parcelas=parcelas,
            )

            total = Decimal("0.00")

            # cria itens + baixa estoque
            for item in carrinho.itens.all():
                produto = mapa_produtos[item.produto_id]

                produto.quantidade -= item.quantidade
                produto.save(update_fields=["quantidade"])

                VendaItem.objects.create(
                    venda=venda,
                    produto=produto,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                )

                total += item.preco_unitario * Decimal(item.quantidade)

            venda.total = total.quantize(Decimal("0.01"))
            venda.save(update_fields=["total", "parcelas"])

            # fecha carrinho
            carrinho.status = "FECHADO"
            carrinho.save(update_fields=["status"])
            carrinho.itens.all().delete()

            # fluxo por forma de pagamento
            if forma.codigo == FormaPagamento.Codigo.PIX:
                messages.info(request, "Agora faça o pagamento via Pix e envie o comprovante.")
                return redirect("pix_pagar", pk=venda.pk)

            if forma.codigo == FormaPagamento.Codigo.VALE:
                messages.success(
                    request,
                    f"Pedido realizado em {parcelas}x no Vale. Aguarde a confirmação do administrador."
                )
                return redirect("minhas_compras")

            messages.success(request, "Pedido realizado! Aguarde a confirmação do administrador.")
            return redirect("minhas_compras")

    else:
        form = CheckoutForm(total=total_preview)

    return render(
        request,
        "website/checkout.html",
        {
            "carrinho": carrinho,
            "form": form,
            "total_preview": total_preview,
        },
    )


# -----------------------
# Detalhe da venda
# -----------------------

@login_required
def venda_detalhe(request, pk):
    venda = get_object_or_404(
        Venda.objects
        .select_related("forma_pagamento", "usuario")
        .prefetch_related("itens__produto"),
        pk=pk,
        usuario=request.user,
    )
    return render(request, "website/venda_detalhe.html", {"venda": venda})


# -----------------------
# Pagamento PIX
# -----------------------

@login_required
def pix_pagar(request, pk):
    venda = get_object_or_404(
        Venda.objects.select_related("forma_pagamento"),
        pk=pk,
        usuario=request.user,
    )

    if venda.forma_pagamento.codigo != FormaPagamento.Codigo.PIX:
        messages.error(request, "Esta venda não é Pix.")
        return redirect("minhas_compras")

    if venda.comprovante_pix:
        messages.info(request, "O comprovante deste pedido já foi enviado.")
        return redirect("minha_compra_detalhe", pk=venda.pk)

    if request.method == "POST":
        form = ComprovantePixForm(request.POST, request.FILES, instance=venda)
        if form.is_valid():
            form.save(update_fields=["comprovante_pix"])
            messages.success(request, "Comprovante enviado! Aguarde a confirmação do administrador.")
            return redirect("minha_compra_detalhe", pk=venda.pk)
    else:
        form = ComprovantePixForm(instance=venda)

    fp = venda.forma_pagamento

    if fp.pix_copia_cola:
        try:
            pix_texto = inserir_ou_atualizar_valor(fp.pix_copia_cola, float(venda.total))
        except Exception:
            pix_texto = fp.pix_copia_cola.strip()
    else:
        pix_texto = f"PIX: {fp.pix_chave} | Valor: R$ {venda.total}"

    return render(
        request,
        "website/pix_pagar.html",
        {
            "venda": venda,
            "form": form,
            "pix_texto": pix_texto,
        },
    )
