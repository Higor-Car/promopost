from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("lojas/", views.lojas, name="lojas"),
    path("categorias/", views.categorias, name="categorias"),
    path("para-lojistas/", views.para_lojistas, name="para_lojistas"),
    path("c/<slug:slug>/", views.comercio, name="comercio"),
    path("p/<int:pk>/", views.promocao, name="promocao"),
    # Saídas que contam o clique antes de ir para o destino
    path("ir/whatsapp/p/<int:pk>/", views.ir_whatsapp_promocao, name="ir_whatsapp_promocao"),
    path("ir/whatsapp/c/<slug:slug>/", views.ir_whatsapp_comercio, name="ir_whatsapp_comercio"),
    path("ir/instagram/<slug:slug>/", views.ir_instagram, name="ir_instagram"),
    path("ir/mapa/<slug:slug>/", views.ir_mapa, name="ir_mapa"),
    # Link privado de resultado para o dono do comércio
    path("resultado/<str:token>/", views.resultado, name="resultado"),
]
