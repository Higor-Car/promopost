from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from .models import Categoria, Cidade, Comercio, Promocao


def inicio(request):
    cidade = request.GET.get("cidade", "")
    if cidade not in Cidade.values:
        cidade = ""

    promocoes = Promocao.objects.ativas().select_related("comercio__categoria")
    if cidade:
        promocoes = promocoes.filter(comercio__cidade=cidade)

    # Só mostra as categorias que têm promoção no ar (na cidade escolhida).
    categorias = (
        Categoria.objects.filter(comercios__promocoes__in=promocoes)
        .annotate(total=Count("comercios__promocoes", distinct=True))
        .order_by("ordem", "nome")
    )

    categoria = None
    slug_categoria = request.GET.get("categoria", "")
    if slug_categoria:
        categoria = Categoria.objects.filter(slug=slug_categoria).first()
    if categoria:
        promocoes = promocoes.filter(comercio__categoria=categoria)

    return render(
        request,
        "vitrine/inicio.html",
        {
            "promocoes": promocoes,
            "cidades": Cidade.choices,
            "cidade": cidade,
            "cidade_nome": Cidade(cidade).label if cidade else "",
            "categorias": categorias,
            "categoria": categoria,
        },
    )


def comercio(request, slug):
    loja = get_object_or_404(Comercio.objects.select_related("categoria"), slug=slug, ativo=True)
    promocoes = loja.promocoes.ativas()
    return render(
        request,
        "vitrine/comercio.html",
        {
            "loja": loja,
            "promocoes": promocoes,
            "whatsapp": loja.link_whatsapp("Olá! Encontrei vocês no Achou Promo."),
        },
    )
