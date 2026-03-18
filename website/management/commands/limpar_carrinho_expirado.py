# website/management/commands/limpar_carrinho_expirado.py
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import RESERVA_HORAS, Carrinho, CarrinhoItem


class Command(BaseCommand):
    help = f"Remove itens de carrinho expirados (>{RESERVA_HORAS}h) e fecha carrinhos vazios"

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=RESERVA_HORAS)

        itens = CarrinhoItem.objects.filter(
            carrinho__status=Carrinho.Status.ABERTO,
            atualizado_em__lt=limite,
        )

        total_itens = itens.count()
        carrinho_ids = list(itens.values_list("carrinho_id", flat=True).distinct())

        itens.delete()

        # Fecha carrinhos que ficaram vazios
        fechados = 0
        if carrinho_ids:
            carrinhos = Carrinho.objects.filter(
                id__in=carrinho_ids,
                status=Carrinho.Status.ABERTO,
            )
            for c in carrinhos:
                if not c.itens.exists():
                    c.status = Carrinho.Status.FECHADO
                    c.save(update_fields=["status"])
                    fechados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{total_itens} itens expirados removidos. {fechados} carrinhos vazios fechados."
            )
        )