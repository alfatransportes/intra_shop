from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import CarrinhoItem


class Command(BaseCommand):
    help = "Remove itens de carrinho que estão há mais de 4 horas sem atualização"

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=4)

        itens = CarrinhoItem.objects.filter(
            carrinho__status="ABERTO",
            atualizado_em__lt=limite,
        )

        total = itens.count()
        itens.delete()

        self.stdout.write(
            self.style.SUCCESS(f"{total} itens de carrinho expirados removidos.")
        )
