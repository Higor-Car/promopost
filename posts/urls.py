from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("c/<slug:slug>/", views.comercio, name="comercio"),
]
