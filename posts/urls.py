from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_promocoes, name="lista_promocoes"),
    path("nova/", views.nova_promocao, name="nova_promocao"),
]
