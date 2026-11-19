"""Imagens "Promoções do dia" para postar no Instagram (1080x1350, retrato 4:5).

Cada imagem mostra até 3 promoções em faixas largas (foto + texto grande), para dar
para ler no celular. Com mais promoções, são geradas várias imagens (carrossel).
"""

import io
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont, ImageOps

LARGURA, ALTURA = 1080, 1350
POR_IMAGEM = 3
MAXIMO = 6

LARANJA = (234, 88, 12)
TEXTO = (28, 25, 23)
SUAVE = (120, 113, 108)
FUNDO = (250, 248, 245)
VERMELHO = (220, 38, 38)
AMARELO = (250, 204, 21)

FONTES = {
    True: [  # negrito
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ],
    False: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
}


def fonte(tamanho, negrito=False):
    for caminho in FONTES[negrito]:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(size=tamanho)


def paginas(promocoes):
    """Divide em grupos de até 3 (cada grupo vira uma imagem do carrossel)."""
    promocoes = list(promocoes)[:MAXIMO]
    return [promocoes[i:i + POR_IMAGEM] for i in range(0, len(promocoes), POR_IMAGEM)]


def _cortar(draw, texto, fnt, largura):
    if draw.textlength(texto, font=fnt) <= largura:
        return texto
    while texto and draw.textlength(texto + "…", font=fnt) > largura:
        texto = texto[:-1]
    return texto.rstrip() + "…"


def _quebrar(draw, texto, fnt, largura, linhas_max):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fnt) <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    if len(linhas) > linhas_max:
        linhas = linhas[:linhas_max]
        linhas[-1] = _cortar(draw, linhas[-1] + " …", fnt, largura).replace(" …", "…")
    return [_cortar(draw, linha, fnt, largura) for linha in linhas]


def _preco(valor):
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _foto(promo, tamanho):
    try:
        with promo.imagem.open("rb") as arquivo:
            im = ImageOps.exif_transpose(Image.open(arquivo)).convert("RGB")
            return ImageOps.fit(im, (tamanho, tamanho), Image.LANCZOS)
    except (OSError, ValueError):
        return Image.new("RGB", (tamanho, tamanho), (239, 235, 230))


def _mascara_arredondada(tamanho, raio):
    mascara = Image.new("L", tamanho, 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, tamanho[0] - 1, tamanho[1] - 1], raio, fill=255)
    return mascara


def gerar_imagem(promocoes, pagina=1, total_paginas=1):
    """Recebe até 3 promoções e devolve os bytes de um PNG 1080x1350."""
    promocoes = list(promocoes)[:POR_IMAGEM]
    im = Image.new("RGB", (LARGURA, ALTURA), FUNDO)
    d = ImageDraw.Draw(im)

    # Cabeçalho
    TOPO = 190
    d.rectangle([0, 0, LARGURA, TOPO], fill=LARANJA)
    d.text((56, 38), "Achou Promo", font=fonte(66, True), fill="white")
    subtitulo = f"Promoções de hoje · {timezone.localdate():%d/%m}"
    if total_paginas > 1:
        subtitulo += f"   ({pagina}/{total_paginas})"
    d.text((58, 120), subtitulo, font=fonte(34), fill=(255, 237, 213))
    selo, fs = "Maurilândia e Turvelândia", fonte(25, True)
    w = d.textlength(selo, font=fs)
    d.rounded_rectangle([LARGURA - 56 - w - 36, 64, LARGURA - 56, 114], 25, fill="white")
    d.text((LARGURA - 56 - w - 18, 74), selo, font=fs, fill=LARANJA)

    # Rodapé
    RODAPE = 120
    d.rectangle([0, ALTURA - RODAPE, LARGURA, ALTURA], fill=TEXTO)
    dominio = settings.SITE_URL.split("://", 1)[-1]
    d.text((56, ALTURA - 98), "Veja todas as promoções em", font=fonte(27), fill=(214, 211, 209))
    d.text((56, ALTURA - 62), dominio, font=fonte(36, True), fill="white")
    if settings.INSTAGRAM_SITE:
        insta, fi = f"@{settings.INSTAGRAM_SITE}", fonte(34, True)
        d.text((LARGURA - 56 - d.textlength(insta, font=fi), ALTURA - 80), insta, font=fi, fill=AMARELO)

    # Faixas das promoções (centralizadas no espaço do meio)
    MARGEM, ESPACO, ALT = 40, 24, 312
    FOTO = ALT - 32
    area = ALTURA - TOPO - RODAPE
    bloco = len(promocoes) * ALT + max(len(promocoes) - 1, 0) * ESPACO
    y = TOPO + (area - bloco) // 2

    f_loja, f_titulo, f_preco, f_de = fonte(26), fonte(38, True), fonte(56, True), fonte(30)
    for promo in promocoes:
        x = MARGEM
        d.rounded_rectangle([x, y, LARGURA - MARGEM, y + ALT], 28, fill="white")

        foto = _foto(promo, FOTO)
        im.paste(foto, (x + 16, y + 16), _mascara_arredondada(foto.size, 20))
        if promo.desconto:
            texto, fd = f"-{promo.desconto}%", fonte(30, True)
            wd = d.textlength(texto, font=fd)
            d.rounded_rectangle([x + 30, y + 30, x + 30 + wd + 26, y + 78], 12, fill=VERMELHO)
            d.text((x + 43, y + 34), texto, font=fd, fill="white")

        tx = x + 16 + FOTO + 28
        tw = LARGURA - MARGEM - 24 - tx
        loja = f"{promo.comercio.nome} · até {timezone.localtime(promo.fim):%d/%m}"
        d.text((tx, y + 26), _cortar(d, loja, f_loja, tw), font=f_loja, fill=SUAVE)
        ty = y + 70
        for linha in _quebrar(d, promo.titulo, f_titulo, tw, 3 if promo.preco is None else 2):
            d.text((tx, ty), linha, font=f_titulo, fill=TEXTO)
            ty += 47
        if promo.preco is not None:
            preco = _preco(promo.preco)
            py = y + ALT - 92
            d.text((tx, py), preco, font=f_preco, fill=LARANJA)
            if promo.preco_de is not None:
                de = _preco(promo.preco_de)
                dx = tx + d.textlength(preco, font=f_preco) + 18
                dy = py + 22
                d.text((dx, dy), de, font=f_de, fill=SUAVE)
                d.line([dx, dy + 19, dx + d.textlength(de, font=f_de), dy + 19], fill=SUAVE, width=3)
        y += ALT + ESPACO

    saida = io.BytesIO()
    im.save(saida, format="PNG", optimize=True)
    return saida.getvalue()
