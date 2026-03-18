# website/views_checkout.py
import base64
from decimal import Decimal
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from website.utils import inserir_ou_atualizar_valor

from .forms import CheckoutForm, ComprovantePixForm
from .models import FormaPagamento, Produto, Venda, VendaItem
from .services.carrinho import get_carrinho_aberto


def _calcular_total_carrinho(carrinho) -> Decimal:
    total = Decimal("0.00")
    for item in carrinho.itens.all():
        total += item.preco_unitario * Decimal(item.quantidade)
    return total.quantize(Decimal("0.01"))


def _gerar_qr_base64(payload: str) -> str:
    """
    Gera um PNG em base64 para renderizar no template.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buff = BytesIO()
    img.save(buff, format="PNG")
    b64 = base64.b64encode(buff.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _payload_fallback(forma: FormaPagamento, total: Decimal) -> str:
    """
    Se o pix_payload não estiver configurado, pelo menos mostra algo útil.
    (Não é payload EMV padrão, mas evita UI vazia em ambiente de teste.)
    """
    total_str = f"{total:.2f}".replace(".", ",")
    partes = []
    if forma.pix_nome:
        partes.append(f"Recebedor: {forma.pix_nome}")
    if forma.pix_chave:
        partes.append(f"Chave Pix: {forma.pix_chave}")
    if forma.pix_cidade:
        partes.append(f"Cidade: {forma.pix_cidade}")
    partes.append(f"Valor: R$ {total_str}")
    return " | ".join(partes)


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

            parcelas = 1
            if forma.codigo == FormaPagamento.Codigo.VALE:
                parcelas = int(form.cleaned_data.get("parcelas") or 1)

            # trava produtos
            produto_ids = list(carrinho.itens.values_list("produto_id", flat=True))
            produtos_travados = Produto.objects.select_for_update().filter(id__in=produto_ids)
            mapa_produtos = {p.id: p for p in produtos_travados}

            # valida estoque (no produto travado)
            for item in carrinho.itens.all():
                produto_travado = mapa_produtos.get(item.produto_id)
                if not produto_travado:
                    messages.error(request, "Produto do carrinho não encontrado. Tente novamente.")
                    return redirect("carrinho_detail")

                if item.quantidade > (produto_travado.quantidade or 0):
                    messages.error(request, f"Estoque insuficiente para {produto_travado.nome}.")
                    return redirect("carrinho_detail")

            venda = Venda.objects.create(
                usuario=request.user,
                forma_pagamento=forma,
                observacao=observacao,
                status=Venda.Status.PENDENTE,
                total=Decimal("0.00"),
                parcelas=parcelas,
            )

            total = Decimal("0.00")

            # cria itens + baixa estoque (usando instância travada)
            for item in carrinho.itens.all():
                produto_travado = mapa_produtos[item.produto_id]

                produto_travado.quantidade -= item.quantidade
                produto_travado.save(update_fields=["quantidade"])

                VendaItem.objects.create(
                    venda=venda,
                    produto=produto_travado,
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


@login_required
def minhas_compras(request):
    vendas = (
        Venda.objects
        .filter(usuario=request.user)
        .select_related("forma_pagamento")
        .order_by("-id")
    )

    return render(
        request,
        "website/minhas_compras.html",
        {
            "vendas": vendas
        }
    )

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

    forma = venda.forma_pagamento

    payload = (forma.pix_payload or "").strip()

    # Se existir payload configurado, tenta atualizar o valor nele
    if payload:
        try:
            payload = inserir_ou_atualizar_valor(payload, float(venda.total))
        except Exception:
            # se falhar, mantém o payload original
            pass
    else:
        # fallback para não deixar UI vazia
        payload = _payload_fallback(forma, venda.total)

    # gera QR code (base64) sempre que possível
    qr_code_data_url = None
    try:
        qr_code_data_url = _gerar_qr_base64(payload)
    except Exception:
        qr_code_data_url = None

    return render(
        request,
        "website/pix_pagar.html",
        {
            "venda": venda,
            "payload": payload,
            "qr_code_data_url": qr_code_data_url,
        },
    )


@login_required
@transaction.atomic
def enviar_comprovante_pix(request, pk):
    venda = get_object_or_404(
        Venda.objects.select_related("forma_pagamento"),
        pk=pk,
        usuario=request.user,
    )

    if venda.forma_pagamento.codigo != FormaPagamento.Codigo.PIX:
        messages.error(request, "Esta venda não é Pix.")
        return redirect("minhas_compras")

    if request.method == "POST":
        form = ComprovantePixForm(request.POST, request.FILES)

        if form.is_valid():
            venda.comprovante_pix = form.cleaned_data["comprovante_pix"]
            venda.save(update_fields=["comprovante_pix"])
            messages.success(request, "Comprovante enviado! Aguarde a confirmação do administrador.")
            return redirect("minhas_compras")
    else:
        form = ComprovantePixForm()

    return render(
        request,
        "website/enviar_comprovante_pix.html",
        {"venda": venda, "form": form},
    )