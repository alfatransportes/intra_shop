# website/views_checkout.py
from decimal import Decimal

# website/views_checkout.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from website.utils import inserir_ou_atualizar_valor

from .forms import CheckoutForm, ComprovantePixForm
from .models import FormaPagamento, Produto, Venda, VendaItem
from .services.carrinho import get_carrinho_aberto


@login_required
@transaction.atomic
def checkout(request):
    carrinho = get_carrinho_aberto(request.user)
    carrinho = (
        carrinho.__class__.objects
        .prefetch_related("itens__produto")
        .select_related("usuario")
        .get(pk=carrinho.pk)
    )

    if not carrinho.itens.exists():
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("index")

    if request.method == "POST":
        print(request.POST)
        form = CheckoutForm(request.POST)
        if form.is_valid():
            forma = form.cleaned_data["forma_pagamento"]
            print("FORMA:", forma.id, forma.nome, forma.codigo)

            obs = form.cleaned_data.get("observacao", "")

            # trava produtos do carrinho
            produto_ids = list(carrinho.itens.values_list("produto_id", flat=True))
            produtos = Produto.objects.select_for_update().filter(id__in=produto_ids)
            mapa = {p.id: p for p in produtos}

            # valida estoque
            for item in carrinho.itens.all():
                p = mapa[item.produto_id]
                if item.quantidade > p.quantidade:
                    messages.error(request, f"Estoque insuficiente para {p.nome}.")
                    return redirect("carrinho_detail")

            # cria venda
            venda = Venda.objects.create(
                usuario=request.user,
                forma_pagamento=forma,
                observacao=obs,
                status=Venda.Status.PENDENTE,
                total=Decimal("0.00"),
            )

            total = Decimal("0.00")

            # cria itens + baixa estoque
            for item in carrinho.itens.all():
                p = mapa[item.produto_id]

                p.quantidade -= item.quantidade
                p.save(update_fields=["quantidade"])

                VendaItem.objects.create(
                    venda=venda,
                    produto=p,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                )
                total += item.preco_unitario * item.quantidade

            venda.total = total.quantize(Decimal("0.01"))
            venda.save(update_fields=["total"])

            # fecha carrinho e limpa itens
            carrinho.status = "FECHADO"
            carrinho.save(update_fields=["status"])
            carrinho.itens.all().delete()

            # fluxo por forma de pagamento
            if forma.codigo == FormaPagamento.Codigo.PIX:

                messages.info(request, "Agora envie o comprovante do Pix para finalizar.")
                return redirect("pix_pagar", pk=venda.pk)

            messages.success(request, "Pedido realizado! Aguarde a confirmação do administrador.")
            return redirect("minhas_compras")
    else:
        form = CheckoutForm()

    return render(request, "website/checkout.html", {"carrinho": carrinho, "form": form})



@login_required
@transaction.atomic
def checkout_confirmar(request, forma_id):
    carrinho = get_carrinho_aberto(request.user)
    forma = get_object_or_404(FormaPagamento, pk=forma_id, ativa=True)

    # Recarrega itens
    carrinho = (
        carrinho.__class__.objects
        .prefetch_related("itens__produto")
        .get(pk=carrinho.pk)
    )

    if not carrinho.itens.exists():
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("carrinho_detail")

    # trava produtos do carrinho (importante!)
    produto_ids = list(carrinho.itens.values_list("produto_id", flat=True))
    produtos_map = {
        p.id: p
        for p in Produto.objects.select_for_update().filter(id__in=produto_ids)
    }

    # valida estoque
    for item in carrinho.itens.all():
        prod = produtos_map.get(item.produto_id)
        if not prod or item.quantidade > prod.quantidade:
            messages.error(request, f"Estoque insuficiente para {item.produto.nome}.")
            return redirect("carrinho_detail")

    # cria venda
    venda = Venda.objects.create(
        usuario=request.user,
        forma_pagamento=forma,
        status=Venda.Status.PENDENTE,
        total=Decimal("0.00"),
    )

    total = Decimal("0.00")

    # cria itens + baixa estoque (já travado)
    for item in carrinho.itens.all():
        prod = produtos_map[item.produto_id]

        VendaItem.objects.create(
            venda=venda,
            produto=prod,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
        )
        total += (item.preco_unitario * Decimal(item.quantidade))

        prod.quantidade -= item.quantidade
        prod.save(update_fields=["quantidade"])

    venda.total = total.quantize(Decimal("0.01"))
    venda.save(update_fields=["total"])

    # fecha carrinho e limpa itens
    carrinho.status = "FECHADO"
    carrinho.save(update_fields=["status"])
    carrinho.itens.all().delete()

    # ✅ fluxo por forma de pagamento
    messages.success(request, "Pedido criado! Aguarde a confirmação do administrador.")

    if forma.codigo == FormaPagamento.Codigo.PIX:
        messages.info(request, "Agora faça o pagamento via Pix e envie o comprovante.")
        return redirect("pix_pagar", pk=venda.pk)

    return redirect("venda_detalhe", pk=venda.pk)


@login_required
def venda_detalhe(request, pk):
    venda = get_object_or_404(Venda, pk=pk, usuario=request.user)
    venda = (
        Venda.objects
        .select_related("forma_pagamento", "usuario")
        .prefetch_related("itens__produto")
        .get(pk=venda.pk)
    )
    return render(request, "website/venda_detalhe.html", {"venda": venda})


@login_required
def pix_pagar(request, pk):
    venda = get_object_or_404(
        Venda.objects.select_related("forma_pagamento"),
        pk=pk,
        usuario=request.user,
    )

    # ✅ garante que é Pix
    if venda.forma_pagamento.codigo != FormaPagamento.Codigo.PIX:

        messages.error(request, "Esta venda não é Pix.")
        return redirect("minhas_compras")

    # ✅ BLOQUEIO: comprovante já enviado
    if venda.comprovante_pix:
        messages.info(request, "O comprovante deste pedido já foi enviado.")
        return redirect("minha_compra_detalhe", pk=venda.pk)

    # daqui pra baixo, só entra se AINDA NÃO enviou comprovante
    if request.method == "POST":
        form = ComprovantePixForm(request.POST, request.FILES, instance=venda)
        if form.is_valid():
            venda = form.save(commit=False)
            venda.save(update_fields=["comprovante_pix"])
            messages.success(
                request,
                "Comprovante enviado! Aguarde a confirmação do administrador."
            )
            return redirect("minha_compra_detalhe", pk=venda.pk)
    else:
        form = ComprovantePixForm(instance=venda)

    # texto do QR
    fp = venda.forma_pagamento

    if fp.pix_copia_cola:
        # ✅ usa BR Code e injeta valor + recalcula CRC
        try:
            pix_texto = inserir_ou_atualizar_valor(fp.pix_copia_cola, float(venda.total))
        except Exception:
            # fallback se o payload estiver inválido
            pix_texto = fp.pix_copia_cola.strip()
    else:
        # ⚠️ aqui ainda NÃO é um PIX válido.
        # Ideal: obrigar pix_copia_cola no cadastro da forma de pagamento.
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
