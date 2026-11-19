from django.contrib import admin

from .models import Comercio, Promocao


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
