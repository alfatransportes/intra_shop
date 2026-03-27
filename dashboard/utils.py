import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)



def enviar_email_status_venda_cliente(venda):
    if not venda.usuario.email:
        return

    cliente = (
        venda.usuario.get_full_name()
        or venda.usuario.username
        or venda.usuario.email
        or "Cliente"
    )

    site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")

    context = {
        "venda": venda,
        "usuario": venda.usuario,
        "cliente": cliente,
        "site_url": site_url,
        "site_name": "Intra Shop",
        "meus_pedidos_url": f"{site_url}/minhas_compras/",
    }

    if venda.status == venda.Status.APROVADA:
        subject = render_to_string(
            "dashboard/emails/venda_aprovada_subject.txt",
            context,
        ).strip()
        body_text = render_to_string(
            "dashboard/emails/venda_aprovada_email.txt",
            context,
        )
        body_html = render_to_string(
            "dashboard/emails/venda_aprovada_email.html",
            context,
        )
    elif venda.status == venda.Status.CANCELADA:
        subject = render_to_string(
            "dashboard/emails/venda_cancelada_subject.txt",
            context,
        ).strip()
        body_text = render_to_string(
            "dashboard/emails/venda_cancelada_email.txt",
            context,
        )
        body_html = render_to_string(
            "dashboard/emails/venda_cancelada_email.html",
            context,
        )
    else:
        return

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[venda.usuario.email],
        )
        email.attach_alternative(body_html, "text/html")
        email.send()
    except Exception:
        logger.exception(
            "Erro ao enviar email de status da venda %s para o cliente",
            venda.pk,
        )