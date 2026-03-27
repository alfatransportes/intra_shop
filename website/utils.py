import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, send_mail
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
        return

    cliente = (
        venda.usuario.get_full_name()
        or venda.usuario.username
        or venda.usuario.email
        or "Cliente"
    )

    context = {
        "venda": venda,
        "usuario": venda.usuario,
        "cliente": cliente,
        "site_url": getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/"),
        "site_name": "Intra Shop",
        "comprovante_enviado": comprovante_enviado,
    }

    if comprovante_enviado:
        subject = render_to_string(
            "website/emails/pix_comprovante_subject.txt",
            context,
        ).strip()
        body_text = render_to_string(
            "website/emails/pix_comprovante_email.txt",
            context,
        )
        body_html = render_to_string(
            "website/emails/pix_comprovante_email.html",
            context,
        )
    else:
        subject = render_to_string(
            "website/emails/nova_compra_subject.txt",
            context,
        ).strip()
        body_text = render_to_string(
            "website/emails/nova_compra_email.txt",
            context,
        )
        body_html = render_to_string(
            "website/emails/nova_compra_email.html",
            context,
        )

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails_staff,
        )
        email.attach_alternative(body_html, "text/html")
        email.send()
    except Exception:
        logger.exception("Falha ao enviar e-mail da venda %s", venda.pk)


def get_config_website():
    return ConfigWebsite.objects.filter(active=True).first()

def get_tipo_produtos():
    return Tipo.objects.all().order_by('nome')


def get_produtos_destaque(limit=12):
    return (
        Produto.objects.select_related("unidade_prod", "tipo_prod", "nivel_ava_prod")
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
        .order_by("-id")[:limit]  # ou "-criado_em" se você tiver esse campo
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
    """
    Recebe um payload PIX (copia e cola) e devolve o payload com campo 54 (valor)
    atualizado e CRC (63) recalculado.

    - Remove o CRC atual
    - Remove campo 54 antigo (se existir)
    - Insere 54 antes do 58 (país) quando possível
    """
    p = (payload or "").strip().replace("\n", "").replace("\r", "")
    if "6304" not in p:
        raise ValueError("Payload PIX inválido: não encontrei o campo 63 (CRC).")

    # remove CRC atual (tudo a partir do 63)
    pos63 = p.rfind("6304")
    sem_crc = p[:pos63]

    # remove campo 54 existente, se houver (54LL<valor>)
    # parsing simples por TLV (EMV): ID(2) + LEN(2) + VALUE(LEN)
    def remover_campo(sem_crc_str: str, campo_id: str) -> str:
        i = 0
        out = ""
        s = sem_crc_str
        while i + 4 <= len(s):
            _id = s[i:i+2]
            ln = int(s[i+2:i+4])
            val_ini = i + 4
            val_fim = val_ini + ln
            if val_fim > len(s):
                # se corrompido, devolve original
                return sem_crc_str
            if _id != campo_id:
                out += s[i:val_fim]
            i = val_fim
        return out

    sem_crc = remover_campo(sem_crc, "54")

    valor_str = f"{float(valor):.2f}"  # 108.00
    campo54 = f"54{len(valor_str):02d}{valor_str}"

    idx58 = sem_crc.find("5802")  # país
    if idx58 != -1:
        novo_sem_crc = sem_crc[:idx58] + campo54 + sem_crc[idx58:]
    else:
        novo_sem_crc = sem_crc + campo54

    base_crc = novo_sem_crc + "6304"
    crc = crc16_ccitt_false(base_crc)
    return base_crc + crc
