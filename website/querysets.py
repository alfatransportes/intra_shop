# website/querysets.py
from django.db.models import F, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import Produto


def produtos_com_estoque_disponivel():
    return (
        Produto.objects
        .prefetch_related("imagens")
        .annotate(
            reservado=Coalesce(
                Sum(
                    "itens_carrinho__quantidade",
                    filter=Q(itens_carrinho__carrinho__status="ABERTO"),
                ),
                Value(0),
            ),
            estoque_disponivel=F("quantidade") - F("reservado"),
        )
    )
