# website/context_processors.py
from .services.carrinho import get_carrinho_aberto
from .utils import get_config_website, get_tipo_produtos


def config_website_global(request):
    config = get_config_website()
    tipos = get_tipo_produtos()

    total_itens = 0
    if request.user.is_authenticated:
        carrinho = get_carrinho_aberto(request.user)
        total_itens = getattr(carrinho, "total_itens", 0)

    return {
        "config_website": config,
        "tipo_produtos": tipos,
        "carrinho_header_total_itens": total_itens,
    }
