from django.db.models import F, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import RESERVA_HORAS, Produto


def produtos_com_estoque_disponivel():
    limite = timezone.now() - RESERVA_HORAS_DELTA()
    return (
        Produto.objects.prefetch_related("imagens", "variacoes")
        .annotate(
            reservado=Coalesce(
                Sum(
                    "itens_carrinho__quantidade",
                    filter=Q(
                        itens_carrinho__carrinho__status="ABERTO",
                        itens_carrinho__atualizado_em__gte=limite,
                    ),
                ),
                Value(0),
                output_field=IntegerField(),
            ),
            estoque_calc=Coalesce(F("quantidade"), Value(0), output_field=IntegerField()) - F("reservado"),
        )
    )


def RESERVA_HORAS_DELTA():
    from datetime import timedelta

    return timedelta(hours=RESERVA_HORAS)
