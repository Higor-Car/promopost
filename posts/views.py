from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import PromocaoForm
from .models import Promocao


def lista_promocoes(request):
    promocoes = Promocao.objects.select_related("comercio")
    return render(request, "posts/lista.html", {"promocoes": promocoes})


def nova_promocao(request):
    if request.method == "POST":
        form = PromocaoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Promoção cadastrada!")
            return redirect("lista_promocoes")
    else:
        form = PromocaoForm()
    return render(request, "posts/form.html", {"form": form})
