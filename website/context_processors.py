# website/context_processors.py
from .utils import get_config_website, get_tipo_produtos


def config_website_global(request):
    return {
        "config_website": get_config_website(),
        "tipo_produtos": get_tipo_produtos(),
    }
