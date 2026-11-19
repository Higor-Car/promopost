from django.contrib import admin, messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .instagram import MAXIMO, gerar_imagem, paginas
from .models import Categoria, Comercio, Promocao, novo_token
from .qr import qr_svg, url_publica

admin.site.site_header = "Achou Promo — administração"
admin.site.site_title = "Achou Promo"
admin.site.index_title = "Cadastros"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("icone", "nome", "slug", "ordem")
    list_display_links = ("nome",)
    list_editable = ("ordem",)
    prepopulated_fields = {"slug": ("nome",)}
    search_fields = ("nome",)


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = (
        "nome", "categoria", "cidade", "whatsapp", "mensalidade", "promocoes_no_ar", "resultado", "ativo",
    )
    list_filter = ("cidade", "categoria", "ativo", "plano")
    search_fields = ("nome", "instagram", "whatsapp")
    prepopulated_fields = {"slug": ("nome",)}
    readonly_fields = ("link_resultado",)
    actions = ("imprimir_qrcodes", "gerar_novo_link_resultado")
    fieldsets = (
        (None, {"fields": ("nome", "slug", "categoria", "cidade", "ativo")}),
        ("Na vitrine", {"fields": ("logo", "capa", "descricao", "horario", "endereco", "whatsapp", "instagram")}),
        ("Contrato", {"fields": ("plano", "mensalidade")}),
        ("Resultado para o dono da loja", {"fields": ("link_resultado",)}),
    )

    def get_queryset(self, request):
        agora = timezone.now()
        return (
            super()
            .get_queryset(request)
            .select_related("categoria")
            .annotate(
                _no_ar=Count("promocoes", filter=Q(promocoes__inicio__lte=agora, promocoes__fim__gt=agora))
            )
        )

    @admin.display(description="promoções no ar", ordering="_no_ar")
    def promocoes_no_ar(self, obj):
        return obj._no_ar

    @admin.display(description="resultado")
    def resultado(self, obj):
        return format_html('<a href="{}" target="_blank">ver</a>', obj.get_resultado_url())

    @admin.display(description="link de resultado")
    def link_resultado(self, obj):
        if not obj.pk:
            return "Aparece depois de salvar."
        url = url_publica(obj.get_resultado_url())
        return format_html(
            '<a href="{0}" target="_blank">{0}</a><br>'
            '<span style="color:#666">Mande este link para o dono da loja: ele mostra visitas, '
            'cliques no WhatsApp e acessos pelo QR code, sem precisar de senha. Se o link vazar, '
            'use a ação "Gerar novo link de resultado" na lista de comércios.</span>',
            url,
        )

    @admin.action(description="Imprimir QR codes (para colar na loja)")
    def imprimir_qrcodes(self, request, queryset):
        cartoes = []
        for loja in queryset.order_by("nome"):
            endereco = url_publica(loja.get_absolute_url())
            cartoes.append({
                "chamada": "Veja as promoções desta loja",
                "loja": loja.nome,
                "endereco": endereco,
                "svg": qr_svg(endereco + "?origem=qr"),
            })
        return render(
            request,
            "admin/posts/qrcodes.html",
            {"cartoes": cartoes, "voltar": reverse("admin:posts_comercio_changelist")},
        )

    @admin.action(description="Gerar novo link de resultado (o antigo para de funcionar)")
    def gerar_novo_link_resultado(self, request, queryset):
        for loja in queryset:
            loja.token_resultado = novo_token()
            loja.save(update_fields=["token_resultado"])
        self.message_user(request, f"Novo link gerado para {queryset.count()} comércio(s).", messages.SUCCESS)


class SituacaoFilter(admin.SimpleListFilter):
    title = "situação"
    parameter_name = "situacao"

    def lookups(self, request, model_admin):
        return [("no_ar", "Na vitrine"), ("futura", "Ainda vai entrar"), ("vencida", "Vencida")]

    def queryset(self, request, queryset):
        agora = timezone.now()
        if self.value() == "no_ar":
            return queryset.filter(inicio__lte=agora, fim__gt=agora)
        if self.value() == "futura":
            return queryset.filter(inicio__gt=agora)
        if self.value() == "vencida":
            return queryset.filter(fim__lte=agora)
        return queryset


@admin.register(Promocao)
class PromocaoAdmin(admin.ModelAdmin):
    list_display = ("miniatura", "titulo", "comercio", "preco", "inicio", "fim", "situacao", "destaque")
    list_display_links = ("miniatura", "titulo")
    list_editable = ("destaque",)
    list_filter = (SituacaoFilter, "destaque", "comercio__cidade", "comercio__categoria", "comercio")
    search_fields = ("titulo", "descricao", "comercio__nome")
    list_select_related = ("comercio",)
    autocomplete_fields = ("comercio",)
    date_hierarchy = "fim"
    actions = ("encerrar_agora", "imagem_instagram")
    change_list_template = "admin/posts/promocao/change_list.html"
    fieldsets = (
        (None, {"fields": ("comercio", "titulo", "descricao", "imagem")}),
        ("Preço (opcional)", {"fields": ("preco_de", "preco")}),
        ("Quando aparece", {"fields": ("inicio", "fim", "destaque")}),
    )

    def get_urls(self):
        extras = [
            path(
                "imagem-do-dia/",
                self.admin_site.admin_view(self.imagem_do_dia),
                name="posts_promocao_imagem_do_dia",
            ),
        ]
        return extras + super().get_urls()

    @admin.display(description="")
    def miniatura(self, obj):
        if not obj.imagem:
            return ""
        return format_html(
            '<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:4px">', obj.imagem.url
        )

    @admin.display(description="situação")
    def situacao(self, obj):
        agora = timezone.now()
        if obj.fim <= agora:
            return "Vencida"
        if obj.inicio > agora:
            return "Ainda vai entrar"
        if not obj.comercio.ativo:
            return "Comércio inativo"
        return "Na vitrine"

    @admin.action(description="Encerrar agora (tirar da vitrine)")
    def encerrar_agora(self, request, queryset):
        agora = timezone.now()
        total = queryset.filter(fim__gt=agora).update(fim=agora)
        self.message_user(request, f"{total} promoção(ões) encerrada(s).", messages.SUCCESS)

    @admin.action(description="Gerar imagem do Instagram com as selecionadas (até 6)")
    def imagem_instagram(self, request, queryset):
        ids = ",".join(str(pk) for pk in queryset.values_list("pk", flat=True)[:MAXIMO])
        url = reverse("admin:posts_promocao_imagem_do_dia") + f"?ids={ids}"
        return render(request, "admin/posts/imagem_do_dia.html", self._contexto_imagem(request, url, queryset))

    def _selecionar(self, request):
        ids = [int(x) for x in request.GET.get("ids", "").split(",") if x.strip().isdigit()][:MAXIMO]
        if ids:
            por_id = {p.pk: p for p in Promocao.objects.filter(pk__in=ids).select_related("comercio")}
            return [por_id[i] for i in ids if i in por_id]
        # Automático: destaques primeiro, depois as que acabam antes.
        return list(Promocao.objects.ativas().select_related("comercio").order_by("-destaque", "fim")[:MAXIMO])

    def _contexto_imagem(self, request, url_base, promocoes):
        separador = "&" if "?" in url_base else "?"
        grupos = paginas(promocoes)
        return {
            **self.admin_site.each_context(request),
            "title": "Imagem do dia para o Instagram",
            "promocoes": [p for g in grupos for p in g],
            "imagens": [
                {
                    "numero": n,
                    "promocoes": grupo,
                    "url_png": f"{url_base}{separador}png=1&pagina={n}",
                    "url_download": f"{url_base}{separador}png=1&pagina={n}&baixar=1",
                }
                for n, grupo in enumerate(grupos, 1)
            ],
            "opts": self.model._meta,
        }

    def imagem_do_dia(self, request):
        promocoes = self._selecionar(request)
        if request.GET.get("png"):
            grupos = paginas(promocoes)
            try:
                n = int(request.GET.get("pagina", 1))
            except ValueError:
                n = 1
            if not 1 <= n <= len(grupos):
                return HttpResponse("Nenhuma promoção no ar.", status=404, content_type="text/plain; charset=utf-8")
            resposta = HttpResponse(gerar_imagem(grupos[n - 1], n, len(grupos)), content_type="image/png")
            if request.GET.get("baixar"):
                nome = f"achoupromo-{timezone.localdate():%Y-%m-%d}-{n}.png"
                resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
            return resposta
        url = request.path + (f"?ids={request.GET['ids']}" if request.GET.get("ids") else "")
        return render(request, "admin/posts/imagem_do_dia.html", self._contexto_imagem(request, url, promocoes))
