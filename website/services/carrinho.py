from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from website.models import RESERVA_HORAS, Carrinho


def limpar_itens_expirados(carrinho: Carrinho) -> int:
    limite = timezone.now() - timedelta(hours=RESERVA_HORAS)
    itens_expirados = carrinho.itens.filter(atualizado_em__lt=limite)
    total = itens_expirados.count()
    if total:
        itens_expirados.delete()
    return total


@transaction.atomic
def get_carrinho_aberto(usuario):
    carrinho, _ = Carrinho.objects.select_for_update().get_or_create(
        usuario=usuario,
        status=Carrinho.Status.ABERTO,
    )
    limpar_itens_expirados(carrinho)
    return carrinho
