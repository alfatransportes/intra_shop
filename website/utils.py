import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models import Prefetch
from django.template.loader import render_to_string

from website.models import ConfigWebsite, Produto, ProdutoImagem, Tipo

logger = logging.getLogger(__name__)
User = get_user_model()


def enviar_email_staff_nova_compra(venda, comprovante_enviado=False):
    emails_staff = list(
        User.objects.filter(is_staff=True, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    if not emails_staff:
        logger.info("Nenhum staff com e-mail para notificação da venda %s", venda.pk)
        return

    cliente = venda.usuario.get_full_name() or venda.usuario.username or venda.usuario.email or "Cliente"
    site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")
    context = {
        "venda": venda,
        "usuario": venda.usuario,
        "cliente": cliente,
        "site_url": site_url,
        "dashboard_venda_url": f"{site_url}/painel-controle/vendas/{venda.pk}/",
        "site_name": "Intra Shop",
        "comprovante_enviado": comprovante_enviado,
    }

    if comprovante_enviado:
        subject_template = "website/emails/pix_comprovante_subject.txt"
        text_template = "website/emails/pix_comprovante_email.txt"
        html_template = "website/emails/pix_comprovante_email.html"
    else:
        subject_template = "website/emails/nova_compra_subject.txt"
        text_template = "website/emails/nova_compra_email.txt"
        html_template = "website/emails/nova_compra_email.html"

    try:
        email = EmailMultiAlternatives(
            subject=render_to_string(subject_template, context).strip(),
            body=render_to_string(text_template, context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails_staff,
        )
        email.attach_alternative(render_to_string(html_template, context), "text/html")
        email.send()
    except Exception:
        logger.exception("Falha ao enviar e-mail da venda %s", venda.pk)


def get_config_website():
    return ConfigWebsite.objects.filter(active=True).first()


def get_tipo_produtos():
    return Tipo.objects.filter(ativo=True).order_by("nome")


def get_produtos_destaque(limit=12):
    return (
        Produto.objects.filter(ativo=True)
        .select_related("unidade_prod", "tipo_prod", "nivel_ava_prod")
        .prefetch_related(
            Prefetch(
                "imagens",
                queryset=ProdutoImagem.objects.filter(principal=True).order_by("ordem", "id"),
                to_attr="imagens_principais",
            ),
            Prefetch(
                "imagens",
                queryset=ProdutoImagem.objects.order_by("ordem", "id"),
                to_attr="imagens_ordenadas",
            ),
        )
        .order_by("-id")[:limit]
    )


def crc16_ccitt_false(data: str) -> str:
    crc = 0xFFFF
    for b in data.encode("utf-8"):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def inserir_ou_atualizar_valor(payload: str, valor: float) -> str:
    p = (payload or "").strip().replace("\n", "").replace("\r", "")
    if "6304" not in p:
        raise ValueError("Payload PIX inválido: não encontrei o campo 63 (CRC).")

    pos63 = p.rfind("6304")
    sem_crc = p[:pos63]

    def remover_campo(sem_crc_str: str, campo_id: str) -> str:
        i = 0
        out = ""
        s = sem_crc_str
        while i + 4 <= len(s):
            _id = s[i:i + 2]
            ln = int(s[i + 2:i + 4])
            val_ini = i + 4
            val_fim = val_ini + ln
            if val_fim > len(s):
                return sem_crc_str
            if _id != campo_id:
                out += s[i:val_fim]
            i = val_fim
        return out

    sem_crc = remover_campo(sem_crc, "54")
    valor_str = f"{Decimal(str(valor)):.2f}"
    campo54 = f"54{len(valor_str):02d}{valor_str}"
    idx58 = sem_crc.find("5802")
    novo_sem_crc = sem_crc[:idx58] + campo54 + sem_crc[idx58:] if idx58 != -1 else sem_crc + campo54
    base_crc = novo_sem_crc + "6304"
    crc = crc16_ccitt_false(base_crc)
    return base_crc + crc
