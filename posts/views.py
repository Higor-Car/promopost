from datetime import datetime
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .agendamento import (
    AgendamentoError,
    agendar_promocao,
    desagendar_promocao,
    marcar_postagem_publicada,
    postagens_na_hora,
)
from .forms import PromocaoForm
from .models import Postagem, Promocao


@login_required
def lista_promocoes(request):
    promocoes = Promocao.objects.select_related("comercio").prefetch_related("postagens")
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
        messages.warning(request, "Promoção publicada ou encerrada não pode mais ser editada.")
        return redirect("lista_promocoes")

    if request.method == "POST":
        imagem_antiga = promocao.imagem.name
        estava_aprovada = promocao.status in (Promocao.Status.APROVADA, Promocao.Status.AGENDADA)
        form = PromocaoForm(request.POST, request.FILES, instance=promocao)
        if form.is_valid():
            promocao = form.save(commit=False)
            if estava_aprovada and form.has_changed():
                # Mudou o conteúdo: cancela o agendamento e precisa ser aprovada de novo.
                promocao.status = Promocao.Status.RASCUNHO
                desagendar_promocao(promocao)
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
        try:
            agendar_promocao(promocao)
        except AgendamentoError as erro:
            messages.warning(request, str(erro))
        else:
            quando = timezone.localtime(promocao.postagens.first().agendada_para)
            messages.success(
                request,
                f"Promoção '{promocao.titulo}' aprovada e agendada para {quando:%d/%m/%Y às %H:%M}.",
            )
    else:
        messages.warning(request, "Só dá para aprovar promoções em rascunho ou aguardando aprovação.")
    return redirect("lista_promocoes")


@login_required
@require_POST
def marcar_publicada(request, pk):
    postagem = get_object_or_404(Postagem.objects.select_related("promocao"), pk=pk)
    try:
        marcar_postagem_publicada(postagem)
    except AgendamentoError as erro:
        messages.warning(request, str(erro))
    else:
        messages.success(
            request, f"{postagem.get_rede_display()} de '{postagem.promocao.titulo}' marcado como publicado."
        )
    proxima = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(proxima, allowed_hosts={request.get_host()}):
        return redirect(proxima)
    return redirect("lista_promocoes")


def _mes_pedido(request):
    """Lê ?mes=AAAA-MM; se vier vazio ou inválido, usa o mês atual."""
    try:
        ano, mes = (int(x) for x in request.GET.get("mes", "").split("-"))
        return datetime(ano, mes, 1).date()
    except (TypeError, ValueError):
        return timezone.localdate().replace(day=1)


def _somar_mes(dia, n):
    total = dia.year * 12 + dia.month - 1 + n
    return dia.replace(year=total // 12, month=total % 12 + 1)


@login_required
def calendario(request):
    inicio_mes = _mes_pedido(request)
    fim_mes = _somar_mes(inicio_mes, 1)
    tz = timezone.get_current_timezone()
    postagens = (
        Postagem.objects.filter(
            agendada_para__gte=datetime.combine(inicio_mes, datetime.min.time(), tz),
            agendada_para__lt=datetime.combine(fim_mes, datetime.min.time(), tz),
        )
        .select_related("promocao__comercio")
        .order_by("agendada_para", "rede")
    )
    agora = timezone.now()
    for postagem in postagens:
        postagem.na_hora = (
            postagem.status == Postagem.Status.PENDENTE
            and postagem.agendada_para <= agora
            and postagem.promocao.status == Promocao.Status.AGENDADA
        )
    dias = [
        (dia, list(itens))
        for dia, itens in groupby(postagens, key=lambda p: timezone.localdate(p.agendada_para))
    ]
    return render(
        request,
        "posts/calendario.html",
        {
            "na_hora": postagens_na_hora(agora),
            "dias": dias,
            "inicio_mes": inicio_mes,
            "mes_anterior": _somar_mes(inicio_mes, -1),
            "mes_seguinte": fim_mes,
            "hoje": timezone.localdate(),
        },
    )
