import io
import re

import qrcode
import qrcode.image.pil
import qrcode.image.svg
from django.conf import settings
from django.utils.safestring import mark_safe


def base_publica():
    """Endereço do site no ar. Usa http enquanto o HTTPS (certificado) não estiver ligado,
    senão o link do dono e o QR code apontariam para um endereço que ainda não abre."""
    base = settings.SITE_URL.rstrip("/")
    if not getattr(settings, "SECURE_SSL_REDIRECT", False) and base.startswith("https://"):
        base = "http://" + base[len("https://"):]
    return base


def url_publica(caminho):
    return base_publica() + caminho


def url_qr_loja(loja):
    """Para onde o QR code da loja leva (com ?origem=qr para contar os acessos)."""
    return url_publica(loja.get_absolute_url()) + "?origem=qr"


def _qr(texto):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
    qr.add_data(texto)
    qr.make(fit=True)
    return qr


def qr_svg(texto):
    """QR code em SVG, para mostrar na tela."""
    svg = _qr(texto).make_image(image_factory=qrcode.image.svg.SvgPathImage).to_string(encoding="unicode")
    # Tira o tamanho fixo (em mm) para o QR ocupar a largura de onde for colocado.
    svg = re.sub(r'^<svg width="[^"]*" height="[^"]*"', '<svg class="qr" style="display:block;width:100%;height:auto"', svg)
    return mark_safe(svg)


def qr_png(texto):
    """QR code em PNG (bytes), para baixar."""
    imagem = _qr(texto).make_image(image_factory=qrcode.image.pil.PilImage)
    saida = io.BytesIO()
    imagem.save(saida, format="PNG")
    return saida.getvalue()
