from datetime import timedelta

from django.db.models import F, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import RESERVA_HORAS, Produto, ProdutoVariacao


def produtos_com_estoque_disponivel():
    limite = timezone.now() - timedelta(hours=RESERVA_HORAS)

    reservado_subquery = (
        Produto.objects.filter(pk=OuterRef("pk"))
        .annotate(
            reservado_calc=Coalesce(
                Sum(
                    "itens_carrinho__quantidade",
                    filter=Q(
                        itens_carrinho__carrinho__status="ABERTO",
                        itens_carrinho__atualizado_em__gte=limite,
                    ),
                ),
                Value(0),
            )
        )
        .values("reservado_calc")[:1]
    )

    estoque_variacoes_subquery = (
        ProdutoVariacao.objects.filter(
            produto=OuterRef("pk"),
            ativo=True,
        )
        .values("produto")
        .annotate(total=Coalesce(Sum("quantidade"), Value(0)))
        .values("total")[:1]
    )

    return (
        Produto.objects
        .select_related("tipo_prod", "unidade_prod", "nivel_ava_prod")
        .prefetch_related("imagens")
        .annotate(
            reservado=Coalesce(
                Subquery(reservado_subquery, output_field=IntegerField()),
                Value(0),
            ),
            estoque_base=Coalesce(
                Subquery(estoque_variacoes_subquery, output_field=IntegerField()),
                F("quantidade"),
                output_field=IntegerField(),
            ),
        )
        .annotate(
            estoque_calc=Coalesce(
                F("estoque_base") - F("reservado"),
                Value(0),
                output_field=IntegerField(),
            )
        )
    )


def RESERVA_HORAS_DELTA():
    from datetime import timedelta

    return timedelta(hours=RESERVA_HORAS)
