from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from . import metricas
from .metricas import Tipo
from .models import Categoria, Cidade, Comercio, MetricaDiaria, Promocao, normalizar


def _ativas():
    return Promocao.objects.ativas().select_related("comercio__categoria")


def _cidade(request):
    cidade = request.GET.get("cidade", "")
    return cidade if cidade in Cidade.values else ""


def _lojas_com_contagem(cidade=""):
    """Lojas ativas com o número de promoções no ar (lojas com promoção primeiro)."""
    agora = timezone.now()
    lojas = Comercio.objects.filter(ativo=True).select_related("categoria").annotate(
        no_ar=Count("promocoes", filter=Q(promocoes__inicio__lte=agora, promocoes__fim__gt=agora))
    )
    if cidade:
        lojas = lojas.filter(cidade=cidade)
    return lojas.order_by("-no_ar", "nome")


def inicio(request):
    cidade = _cidade(request)
    busca = request.GET.get("q", "").strip()[:80]

    promocoes = list(_ativas())
    if cidade:
        promocoes = [p for p in promocoes if p.comercio.cidade == cidade]

    # Categorias com promoção no ar (na cidade escolhida): só as 6 com mais ofertas,
    # para não encher a tela; as outras ficam na página Categorias.
    contagem = Counter(p.comercio.categoria_id for p in promocoes)
    categorias = list(Categoria.objects.filter(pk__in=contagem))
    for c in categorias:
        c.total = contagem[c.pk]
    categorias.sort(key=lambda c: (-c.total, c.ordem, c.nome))

    categoria = None
    slug_categoria = request.GET.get("categoria", "")
    if slug_categoria:
        categoria = Categoria.objects.filter(slug=slug_categoria).first()
    if categoria:
        promocoes = [p for p in promocoes if p.comercio.categoria_id == categoria.pk]

    mais_categorias = len(categorias) > 6
    visiveis = categorias[:6]
    if categoria and categoria not in visiveis and categoria in categorias:
        visiveis.append(categoria)  # a escolhida sempre aparece
    categorias = visiveis

    if busca:
        palavras = normalizar(busca).split()
        promocoes = [p for p in promocoes if all(w in p.texto_busca() for w in palavras)]

    filtrando = bool(busca or categoria)
    destaques = [] if filtrando else [p for p in promocoes if p.destaque]
    acabando = [] if filtrando else [p for p in promocoes if p.acaba_hoje and p not in destaques]
    demais = [p for p in promocoes if p not in destaques and p not in acabando]

    lojas = []
    if not filtrando:
        lojas = [loja for loja in _lojas_com_contagem(cidade) if loja.no_ar][:12]

    metricas.registrar_varios(request, Tipo.IMPRESSAO, [(p.comercio_id, p.pk) for p in promocoes])

    return render(
        request,
        "vitrine/inicio.html",
        {
            "menu": "inicio",
            "destaques": destaques,
            "acabando": acabando,
            "promocoes": demais,
            "lojas": lojas,
            "capa": (destaques or demais or acabando or [None])[0],
            "total": len(promocoes),
            "cidades": Cidade.choices,
            "cidade": cidade,
            "cidade_nome": Cidade(cidade).label if cidade else "",
            "categorias": categorias,
            "mais_categorias": mais_categorias,
            "categoria": categoria,
            "busca": busca,
            "filtrando": filtrando,
        },
    )


def lojas(request):
    cidade = _cidade(request)
    todas = list(_lojas_com_contagem(cidade))
    categorias = sorted({loja.categoria for loja in todas}, key=lambda c: (c.ordem, c.nome))
    categoria = None
    slug = request.GET.get("categoria", "")
    if slug:
        categoria = next((c for c in categorias if c.slug == slug), None)
    if categoria:
        todas = [loja for loja in todas if loja.categoria_id == categoria.pk]
    return render(
        request,
        "vitrine/lojas.html",
        {
            "menu": "lojas",
            "lojas": todas,
            "cidades": Cidade.choices,
            "cidade": cidade,
            "cidade_nome": Cidade(cidade).label if cidade else "",
            "categorias": categorias,
            "categoria": categoria,
        },
    )


def categorias(request):
    contagem = Counter(p.comercio.categoria_id for p in _ativas())
    lista = list(Categoria.objects.annotate(lojas=Count("comercios", filter=Q(comercios__ativo=True))))
    for c in lista:
        c.total = contagem.get(c.pk, 0)
    # Só categorias que têm loja ou oferta; as vazias só poluem a tela.
    lista = [c for c in lista if c.total or c.lojas]
    lista.sort(key=lambda c: (c.total == 0, -c.total, c.ordem, c.nome))
    return render(request, "vitrine/categorias.html", {"menu": "categorias", "categorias": lista})


def para_lojistas(request):
    agora = timezone.now()
    inicio_mes = timezone.localdate() - timedelta(days=29)
    numeros = {
        "lojas": Comercio.objects.filter(ativo=True).count(),
        "promocoes": Promocao.objects.ativas(agora).count(),
        "visitas": MetricaDiaria.objects.filter(
            dia__gte=inicio_mes, tipo__in=[Tipo.VISITA_COMERCIO, Tipo.VISITA_PROMOCAO]
        ).aggregate(n=Sum("total"))["n"] or 0,
        "whatsapp": MetricaDiaria.objects.filter(dia__gte=inicio_mes, tipo=Tipo.WHATSAPP)
        .aggregate(n=Sum("total"))["n"] or 0,
    }
    # Só mostra os números quando já impressionam; no começo eles mais atrapalham que ajudam.
    mostrar_numeros = numeros["lojas"] >= 5 and numeros["visitas"] >= 300
    return render(
        request,
        "vitrine/para_lojistas.html",
        {"menu": "lojistas", "numeros": numeros, "mostrar_numeros": mostrar_numeros},
    )


def comercio(request, slug):
    loja = get_object_or_404(Comercio.objects.select_related("categoria"), slug=slug, ativo=True)
    promocoes = list(loja.promocoes.ativas().select_related("comercio__categoria"))

    metricas.registrar(request, Tipo.VISITA_COMERCIO, loja.pk)
    if request.GET.get("origem") == "qr":
        metricas.registrar(request, Tipo.QR, loja.pk)
    metricas.registrar_varios(request, Tipo.IMPRESSAO, [(loja.pk, p.pk) for p in promocoes])

    aba = "info" if request.GET.get("aba") == "info" else "promocoes"
    return render(
        request,
        "vitrine/comercio.html",
        {"menu": "lojas", "loja": loja, "promocoes": promocoes, "aba": aba},
    )


def promocao(request, pk):
    promo = get_object_or_404(Promocao.objects.select_related("comercio__categoria"), pk=pk)
    if not promo.comercio.ativo:
        raise Http404
    if not promo.ativa:
        # Promoção vencida ou que ainda não começou: mostra aviso e as outras da loja.
        outras = list(promo.comercio.promocoes.ativas().select_related("comercio__categoria")[:6])
        return render(request, "vitrine/promocao_encerrada.html", {"promo": promo, "outras": outras}, status=410)

    metricas.registrar(request, Tipo.VISITA_PROMOCAO, promo.comercio_id, promo.pk)
    outras = list(
        promo.comercio.promocoes.ativas().exclude(pk=promo.pk).select_related("comercio__categoria")[:6]
    )
    return render(
        request, "vitrine/promocao.html", {"menu": "inicio", "promo": promo, "loja": promo.comercio, "outras": outras}
    )


# ---- Links de saída: contam o clique e mandam para o destino ----

def ir_whatsapp_promocao(request, pk):
    promo = get_object_or_404(Promocao.objects.select_related("comercio"), pk=pk, comercio__ativo=True)
    destino = promo.link_whatsapp()
    if not destino:
        raise Http404
    metricas.registrar(request, Tipo.WHATSAPP, promo.comercio_id, promo.pk)
    return redirect(destino)


def ir_whatsapp_comercio(request, slug):
    loja = get_object_or_404(Comercio, slug=slug, ativo=True)
    destino = loja.link_whatsapp("Olá! Encontrei vocês no Achou Promo.")
    if not destino:
        raise Http404
    metricas.registrar(request, Tipo.WHATSAPP, loja.pk)
    return redirect(destino)


def ir_instagram(request, slug):
    loja = get_object_or_404(Comercio, slug=slug, ativo=True)
    if not loja.instagram_usuario:
        raise Http404
    metricas.registrar(request, Tipo.INSTAGRAM, loja.pk)
    return redirect(f"https://instagram.com/{loja.instagram_usuario}")


def ir_mapa(request, slug):
    loja = get_object_or_404(Comercio, slug=slug, ativo=True)
    if not loja.link_mapa:
        raise Http404
    metricas.registrar(request, Tipo.MAPA, loja.pk)
    return redirect(loja.link_mapa)


# ---- Resultado para o dono do comércio (link privado) ----

PERIODOS = (7, 30, 90)


@never_cache
def resultado(request, token):
    loja = get_object_or_404(Comercio.objects.select_related("categoria"), token_resultado=token)
    try:
        dias = int(request.GET.get("dias", 30))
    except ValueError:
        dias = 30
    if dias not in PERIODOS:
        dias = 30
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=dias - 1)
    base = MetricaDiaria.objects.filter(comercio=loja, dia__gte=inicio, dia__lte=hoje)

    totais = defaultdict(int, {
        linha["tipo"]: linha["n"] for linha in base.values("tipo").annotate(n=Sum("total"))
    })

    # Gráfico: visitas (loja + promoções) e cliques no WhatsApp por dia.
    por_dia = defaultdict(lambda: {"visitas": 0, "whatsapp": 0})
    for linha in base.values("dia", "tipo").annotate(n=Sum("total")):
        if linha["tipo"] in (Tipo.VISITA_COMERCIO, Tipo.VISITA_PROMOCAO):
            por_dia[linha["dia"]]["visitas"] += linha["n"]
        elif linha["tipo"] == Tipo.WHATSAPP:
            por_dia[linha["dia"]]["whatsapp"] += linha["n"]
    maximo = max([v["visitas"] for v in por_dia.values()] + [1])
    grafico = []
    for i in range(dias):
        dia = inicio + timedelta(days=i)
        v = por_dia.get(dia, {"visitas": 0, "whatsapp": 0})
        grafico.append({"dia": dia, **v, "altura": round(100 * v["visitas"] / maximo)})

    # Tabela por promoção.
    linhas = defaultdict(lambda: defaultdict(int))
    for linha in base.exclude(promocao=None).values("promocao", "tipo").annotate(n=Sum("total")):
        linhas[linha["promocao"]][linha["tipo"]] = linha["n"]
    promos = {p.pk: p for p in Promocao.objects.filter(pk__in=linhas)}
    tabela = sorted(
        (
            {
                "promo": promos[pk],
                "impressoes": t[Tipo.IMPRESSAO],
                "visitas": t[Tipo.VISITA_PROMOCAO],
                "whatsapp": t[Tipo.WHATSAPP],
            }
            for pk, t in linhas.items()
            if pk in promos
        ),
        key=lambda x: (x["whatsapp"], x["visitas"], x["impressoes"]),
        reverse=True,
    )

    response = render(
        request,
        "vitrine/resultado.html",
        {
            "loja": loja,
            "dias": dias,
            "periodos": PERIODOS,
            "inicio": inicio,
            "hoje": hoje,
            "visitas": totais[Tipo.VISITA_COMERCIO] + totais[Tipo.VISITA_PROMOCAO],
            "impressoes": totais[Tipo.IMPRESSAO],
            "whatsapp": totais[Tipo.WHATSAPP],
            "qr": totais[Tipo.QR],
            "instagram": totais[Tipo.INSTAGRAM],
            "mapa": totais[Tipo.MAPA],
            "grafico": grafico,
            "rotulos": [g["dia"] for g in grafico] if dias == 7 else [inicio, inicio + timedelta(days=dias // 2), hoje],
            "tabela": tabela,
            "no_ar": loja.promocoes.ativas().count(),
        },
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
