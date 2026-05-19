from django.apps import AppConfig
from django.db.models.signals import post_migrate


def criar_unidade_matriz(sender, **kwargs):
    Unidade = sender.get_model("Unidade")

    Unidade.objects.get_or_create(
        codigo=1,
        defaults={"nome": "Matriz"}
    )


class WebsiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "website"

    def ready(self):
        post_migrate.connect(criar_unidade_matriz, sender=self)