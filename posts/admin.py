from django.contrib import admin, messages
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Categoria, Comercio, Promocao
from .qr import qr_svg, url_publica

admin.site.site_header = "Achou Promo — administração"
admin.site.site_title = "Achou Promo"
admin.site.index_title = "Cadastros"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ordem")
    list_editable = ("ordem",)
    prepopulated_fields = {"slug": ("nome",)}
    search_fields = ("nome",)


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "cidade", "whatsapp", "mensalidade", "promocoes_no_ar", "ativo")
    list_filter = ("cidade", "categoria", "ativo", "plano")
    search_fields = ("nome", "instagram", "whatsapp")
    prepopulated_fields = {"slug": ("nome",)}
    actions = ("imprimir_qrcodes",)
    fieldsets = (
        (None, {"fields": ("nome", "slug", "categoria", "cidade", "ativo")}),
        ("Na vitrine", {"fields": ("logo", "descricao", "endereco", "whatsapp", "instagram")}),
        ("Contrato", {"fields": ("plano", "mensalidade")}),
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
    actions = ("encerrar_agora",)
    fieldsets = (
        (None, {"fields": ("comercio", "titulo", "descricao", "imagem")}),
        ("Preço (opcional)", {"fields": ("preco_de", "preco")}),
        ("Quando aparece", {"fields": ("inicio", "fim", "destaque")}),
    )

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
