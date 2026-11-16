from django.contrib import admin

from .models import Comercio, Postagem, Promocao


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ("nome", "cidade", "plano", "mensalidade", "ativo")
    list_filter = ("cidade", "plano", "ativo")
    search_fields = ("nome", "instagram")


@admin.register(Promocao)
class PromocaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "comercio", "inicio", "fim", "status")
    list_filter = ("status", "comercio")
    search_fields = ("titulo", "comercio__nome")


@admin.register(Postagem)
class PostagemAdmin(admin.ModelAdmin):
    list_display = ("promocao", "rede", "agendada_para", "status")
    list_filter = ("rede", "status")
