from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_promocoes, name="lista_promocoes"),
    path("nova/", views.nova_promocao, name="nova_promocao"),
    path("calendario/", views.calendario, name="calendario"),
    path("<int:pk>/editar/", views.editar_promocao, name="editar_promocao"),
    path("<int:pk>/excluir/", views.excluir_promocao, name="excluir_promocao"),
    path("<int:pk>/aprovar/", views.aprovar_promocao, name="aprovar_promocao"),
    path("postagens/<int:pk>/publicada/", views.marcar_publicada, name="marcar_publicada"),
]
