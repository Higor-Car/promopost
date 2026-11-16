from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PromocaoForm
from .models import Promocao


@login_required
def lista_promocoes(request):
    promocoes = Promocao.objects.select_related("comercio")
    return render(request, "posts/lista.html", {"promocoes": promocoes})


@login_required
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


@login_required
@require_POST
def aprovar_promocao(request, pk):
    promocao = get_object_or_404(Promocao, pk=pk)
    if promocao.status in (Promocao.Status.RASCUNHO, Promocao.Status.AGUARDANDO):
        promocao.status = Promocao.Status.APROVADA
        promocao.save(update_fields=["status"])
        messages.success(request, f"Promoção '{promocao.titulo}' aprovada!")
    else:
        messages.warning(request, "Só dá para aprovar promoções em rascunho ou aguardando aprovação.")
    return redirect("lista_promocoes")
