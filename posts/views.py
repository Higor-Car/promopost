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
    return render(request, "posts/form.html", {"form": form, "titulo": "Nova promoção"})


@login_required
def editar_promocao(request, pk):
    promocao = get_object_or_404(Promocao, pk=pk)
    if not promocao.pode_editar:
        messages.warning(request, "Promoção agendada, publicada ou encerrada não pode mais ser editada.")
        return redirect("lista_promocoes")

    if request.method == "POST":
        imagem_antiga = promocao.imagem.name
        estava_aprovada = promocao.status == Promocao.Status.APROVADA
        form = PromocaoForm(request.POST, request.FILES, instance=promocao)
        if form.is_valid():
            promocao = form.save(commit=False)
            if estava_aprovada and form.has_changed():
                # Mudou o conteúdo: precisa ser aprovada de novo.
                promocao.status = Promocao.Status.RASCUNHO
            promocao.save()
            if promocao.imagem.name != imagem_antiga:
                promocao.imagem.storage.delete(imagem_antiga)
            if estava_aprovada and promocao.status == Promocao.Status.RASCUNHO:
                messages.warning(request, "Promoção alterada. Ela voltou para rascunho e precisa ser aprovada de novo.")
            else:
                messages.success(request, "Promoção atualizada!")
            return redirect("lista_promocoes")
    else:
        form = PromocaoForm(instance=promocao)
    return render(
        request,
        "posts/form.html",
        {"form": form, "titulo": f"Editar: {promocao.titulo}", "promocao": promocao},
    )


@login_required
def excluir_promocao(request, pk):
    promocao = get_object_or_404(Promocao, pk=pk)
    if not promocao.pode_excluir:
        messages.warning(request, "Promoção publicada não pode ser excluída (fica no histórico).")
        return redirect("lista_promocoes")

    if request.method == "POST":
        titulo, imagem = promocao.titulo, promocao.imagem
        promocao.delete()
        if imagem:
            imagem.storage.delete(imagem.name)
        messages.success(request, f"Promoção '{titulo}' excluída.")
        return redirect("lista_promocoes")
    return render(request, "posts/confirmar_exclusao.html", {"promocao": promocao})


@login_required
@require_POST
def aprovar_promocao(request, pk):
    promocao = get_object_or_404(Promocao, pk=pk)
    if promocao.pode_aprovar:
        promocao.status = Promocao.Status.APROVADA
        promocao.save(update_fields=["status"])
        messages.success(request, f"Promoção '{promocao.titulo}' aprovada!")
    else:
        messages.warning(request, "Só dá para aprovar promoções em rascunho ou aguardando aprovação.")
    return redirect("lista_promocoes")
