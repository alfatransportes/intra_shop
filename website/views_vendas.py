# views_vendas.py
from decimal import ROUND_HALF_UP, Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .models import FormaPagamento, Venda


@login_required
def minhas_compras(request):
    qs = (
        Venda.objects
        .filter(usuario=request.user)
        .select_related("forma_pagamento")
        .prefetch_related("itens__produto")  # melhora o template (itens.0.produto.nome)
        .order_by("-id")
    )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # flag para o template
    for v in page_obj.object_list:
        v.precisa_comprovante_pix = (
            v.forma_pagamento
            and getattr(v.forma_pagamento, "codigo", None) == FormaPagamento.Codigo.PIX
            and v.status == Venda.Status.PENDENTE
            and not v.comprovante_pix
        )

    return render(request, "website/minhas_compras.html", {"page_obj": page_obj})




@login_required
def minha_compra_detalhe(request, pk):
    venda = get_object_or_404(
        Venda.objects.select_related("forma_pagamento").prefetch_related("itens__produto"),
        pk=pk,
    )

    if venda.usuario_id != request.user.id:
        messages.error(request, "Você não tem permissão para acessar essa compra.")
        return redirect("index")

    valor_parcela = None
    if venda.forma_pagamento and venda.forma_pagamento.codigo == FormaPagamento.Codigo.VALE:
        p = int(venda.parcelas or 1)
        if p < 1:
            p = 1
        valor_parcela = (venda.total / Decimal(p)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return render(
        request,
        "website/minha_compra_detalhe.html",
        {"venda": venda, "valor_parcela": valor_parcela},
    )
