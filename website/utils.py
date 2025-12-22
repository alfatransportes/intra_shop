from website.models import ConfigWebsite, Tipo


def get_config_website():
    return ConfigWebsite.objects.filter(active=True).first()

def get_tipo_produtos():
    return Tipo.objects.all().order_by('nome')