# website/services/carrinho.py
from datetime import timedelta

from django.utils import timezone

from website.models import RESERVA_HORAS, Carrinho


def get_carrinho_aberto(usuario):
    carrinho, _ = Carrinho.objects.get_or_create(
        usuario=usuario,
        status=Carrinho.Status.ABERTO,
    )

    # Limpa itens expirados (reserva não pode prender estoque)
    limite = timezone.now() - timedelta(hours=RESERVA_HORAS)
    carrinho.itens.filter(atualizado_em__lt=limite).delete()

    return carrinho