import qrcode
import qrcode.image.svg
from django.conf import settings
from django.utils.safestring import mark_safe


def url_publica(caminho):
    """Endereço completo no site no ar (SITE_URL), para imprimir em QR code."""
    return settings.SITE_URL + caminho


def qr_svg(texto):
    """QR code em SVG (vetorial: fica nítido em qualquer tamanho de impressão)."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=2,
        image_factory=qrcode.image.svg.SvgPathImage,
    )
    qr.add_data(texto)
    qr.make(fit=True)
    svg = qr.make_image().to_string(encoding="unicode")
    return mark_safe(svg)
