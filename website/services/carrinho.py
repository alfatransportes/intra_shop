from website.models import Carrinho


def get_carrinho_aberto(usuario):
    carrinho, _ = Carrinho.objects.get_or_create(
        usuario=usuario,
        status=Carrinho.Status.ABERTO,
    )
    return carrinho
