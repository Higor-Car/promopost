from urllib.parse import quote

from django.conf import settings


def site(request):
    """Dados do Achou Promo usados em todas as páginas (rodapé, compartilhar, anuncie)."""
    contato = settings.CONTATO_WHATSAPP
    anuncie = ""
    if contato:
        mensagem = "Olá! Tenho um comércio e quero anunciar no Achou Promo."
        anuncie = f"https://wa.me/{contato}?text={quote(mensagem)}"
    return {
        "SITE_URL": settings.SITE_URL,
        "INSTAGRAM_SITE": settings.INSTAGRAM_SITE,
        "LINK_ANUNCIE": anuncie,
    }
