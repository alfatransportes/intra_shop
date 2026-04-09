import base64
import logging
from decimal import Decimal
from io import BytesIO

import qrcode
import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from website.utils import inserir_ou_atualizar_valor

from .forms import CheckoutForm, ComprovantePixForm
from .models import FormaPagamento, Produto, ProdutoVariacao, Venda, VendaItem
from .services.carrinho import get_carrinho_aberto
from .services.rastreamento import RastreamentoConfigError, consultar_minuta
from .utils import enviar_email_staff_nova_compra

logger = logging.getLogger(__name__)


def _calcular_total_carrinho(carrinho) -> Decimal:
    total = Decimal("0.00")
    for item in carrinho.itens.all():
        total += item.preco_unitario * Decimal(item.quantidade)
    return total.quantize(Decimal("0.01"))


def _gerar_qr_base64(payload: str) -> str:
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
@require_http_methods(["GET", "POST"])
@transaction.atomic
def checkout(request):
    carrinho = get_carrinho_aberto(request.user)
    carrinho = (
        carrinho.__class__.objects.select_related("usuario")
        .prefetch_related("itens__produto", "itens__variacao")
        .get(pk=carrinho.pk)
    )

    if not carrinho.itens.exists():
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("index")

    total_preview = _calcular_total_carrinho(carrinho)
    if request.method == "GET":
        form = CheckoutForm(total=total_preview)
        return render(
            request,
            "website/checkout.html",
            {"carrinho": carrinho, "form": form, "total_preview": total_preview},
        )

    form = CheckoutForm(request.POST, total=total_preview)
    if not form.is_valid():
        return render(
            request,
            "website/checkout.html",
            {"carrinho": carrinho, "form": form, "total_preview": total_preview},
        )

    forma = form.cleaned_data["forma_pagamento"]
    observacao = (form.cleaned_data.get("observacao") or "").strip()
    parcelas = int(form.cleaned_data.get("parcelas") or 1)

    produto_ids = list(carrinho.itens.values_list("produto_id", flat=True))
    variacao_ids = list(carrinho.itens.exclude(variacao_id=None).values_list("variacao_id", flat=True))

    produtos_travados = Produto.objects.select_for_update().filter(id__in=produto_ids)
    variacoes_travadas = ProdutoVariacao.objects.select_for_update().filter(id__in=variacao_ids)
    mapa_produtos = {p.id: p for p in produtos_travados}
    mapa_variacoes = {v.id: v for v in variacoes_travadas}

    for item in carrinho.itens.all():
        produto_travado = mapa_produtos.get(item.produto_id)
        if not produto_travado:
            messages.error(request, "Produto do carrinho não encontrado. Tente novamente.")
            return redirect("carrinho_detail")

        if item.variacao_id:
            variacao_travada = mapa_variacoes.get(item.variacao_id)
            if not variacao_travada or variacao_travada.produto_id != produto_travado.id:
                messages.error(request, f"Variação inválida para {produto_travado.nome}.")
                return redirect("carrinho_detail")
            if item.quantidade > int(variacao_travada.quantidade or 0):
                messages.error(request, f"Estoque insuficiente para {produto_travado.nome} - {variacao_travada.tamanho}.")
                return redirect("carrinho_detail")
        else:
            if item.quantidade > int(produto_travado.quantidade or 0):
                messages.error(request, f"Estoque insuficiente para {produto_travado.nome}.")
                return redirect("carrinho_detail")
            permitido, erro = produto_travado.pode_finalizar_no_checkout(request.user, item.quantidade)
            if not permitido:
                messages.error(request, erro)
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
    for item in carrinho.itens.all():
        produto_travado = mapa_produtos[item.produto_id]
        variacao_travada = mapa_variacoes.get(item.variacao_id) if item.variacao_id else None

        if variacao_travada:
            variacao_travada.quantidade -= item.quantidade
            variacao_travada.save(update_fields=["quantidade"])
        else:
            produto_travado.quantidade -= item.quantidade
            produto_travado.save(update_fields=["quantidade"])

        VendaItem.objects.create(
            venda=venda,
            produto=produto_travado,
            variacao=variacao_travada,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
        )
        total += item.preco_unitario * Decimal(item.quantidade)

    venda.total = total.quantize(Decimal("0.01"))
    venda.save(update_fields=["total", "parcelas"])
    carrinho.itens.all().delete()
    carrinho.status = carrinho.Status.FECHADO
    carrinho.save(update_fields=["status"])

    if forma.codigo != FormaPagamento.Codigo.PIX:
        transaction.on_commit(lambda: enviar_email_staff_nova_compra(venda))

    if forma.codigo == FormaPagamento.Codigo.PIX:
        messages.info(request, "Agora faça o pagamento via Pix e envie o comprovante.")
        return redirect("pix_pagar", pk=venda.pk)
    if forma.codigo == FormaPagamento.Codigo.VALE:
        messages.success(request, f"Pedido realizado em {parcelas}x no Vale. Aguarde a confirmação do administrador.")
        return redirect("minhas_compras")

    messages.success(request, "Pedido realizado! Aguarde a confirmação do administrador.")
    return redirect("minhas_compras")


@login_required
@require_GET
def minhas_compras(request):
    vendas = (
        Venda.objects.filter(usuario=request.user)
        .select_related("forma_pagamento")
        .prefetch_related("itens__produto", "itens__variacao")
        .order_by("-id")
    )
    return render(request, "website/minhas_compras.html", {"vendas": vendas})


@login_required
@require_GET
def venda_detalhe(request, pk):
    venda = get_object_or_404(
        Venda.objects.select_related("forma_pagamento", "usuario").prefetch_related("itens__produto", "itens__variacao"),
        pk=pk,
        usuario=request.user,
    )
    return render(request, "website/venda_detalhe.html", {"venda": venda})


@login_required
@require_GET
def rastrear_encomenda_json(request, pk):
    venda = get_object_or_404(Venda.objects.select_related("usuario"), pk=pk, usuario=request.user)
    if not venda.minuta:
        return JsonResponse({"ok": False, "erro": "Esta venda ainda não possui minuta de envio."}, status=400)
    try:
        dados = consultar_minuta(venda.minuta)
        return JsonResponse({"ok": True, "dados": dados})
    except RastreamentoConfigError as exc:
        logger.warning("Rastreamento não configurado: %s", exc)
        return JsonResponse({"ok": False, "erro": "Rastreamento indisponível no momento."}, status=503)
    except requests.RequestException:
        return JsonResponse({"ok": False, "erro": "Não foi possível consultar o rastreamento no momento."}, status=502)
    except Exception:
        logger.exception("Erro inesperado ao consultar minuta %s", venda.minuta)
        return JsonResponse({"ok": False, "erro": "Ocorreu um erro inesperado ao consultar a minuta."}, status=500)


@login_required
@require_GET
def pix_pagar(request, pk):
    venda = get_object_or_404(Venda.objects.select_related("forma_pagamento"), pk=pk, usuario=request.user)
    if venda.forma_pagamento.codigo != FormaPagamento.Codigo.PIX:
        messages.error(request, "Esta venda não é Pix.")
        return redirect("minhas_compras")

    payload = (venda.forma_pagamento.pix_payload or "").strip()
    if payload:
        try:
            payload = inserir_ou_atualizar_valor(payload, float(venda.total))
        except Exception:
            logger.exception("Falha ao atualizar payload PIX da venda %s", venda.pk)
    else:
        payload = _payload_fallback(venda.forma_pagamento, venda.total)

    qr_code_data_url = None
    try:
        qr_code_data_url = _gerar_qr_base64(payload)
    except Exception:
        logger.exception("Falha ao gerar QR Code PIX da venda %s", venda.pk)

    return render(request, "website/pix_pagar.html", {"venda": venda, "payload": payload, "qr_code_data_url": qr_code_data_url})


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def enviar_comprovante_pix(request, pk):
    venda = get_object_or_404(Venda.objects.select_related("forma_pagamento", "usuario"), pk=pk, usuario=request.user)
    if venda.forma_pagamento.codigo != FormaPagamento.Codigo.PIX:
        messages.error(request, "Esta venda não é Pix.")
        return redirect("minhas_compras")

    if request.method == "GET":
        return render(request, "website/enviar_comprovante_pix.html", {"venda": venda, "form": ComprovantePixForm()})

    form = ComprovantePixForm(request.POST, request.FILES)
    if form.is_valid():
        venda.comprovante_pix = form.cleaned_data["comprovante_pix"]
        venda.save(update_fields=["comprovante_pix"])
        transaction.on_commit(lambda: enviar_email_staff_nova_compra(venda, comprovante_enviado=True))
        messages.success(request, "Comprovante enviado! Aguarde a confirmação do administrador.")
        return redirect("minhas_compras")

    return render(request, "website/enviar_comprovante_pix.html", {"venda": venda, "form": form})
