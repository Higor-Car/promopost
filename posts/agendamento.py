"""Regras de agendamento das promoções.

Fluxo:
    aprovar -> agendar_promocao() cria uma Postagem por rede e a promoção fica "Agendada";
    o comando `processar_agendamentos` (rodado de tempos em tempos) encerra promoções
    vencidas e marca como "Publicada" quando todas as postagens foram ao ar.

Enquanto a publicação pela API da Meta (Fase 4) não existe, a postagem é feita à mão:
no horário ela aparece como "Hora de postar" no calendário e alguém marca como publicada.
"""

from django.db import transaction
from django.utils import timezone

from .models import Postagem, Promocao


class AgendamentoError(Exception):
    pass


@transaction.atomic
def agendar_promocao(promocao, agora=None):
    """Cria as postagens (Instagram e Facebook) e deixa a promoção como Agendada."""
    agora = agora or timezone.now()
    if promocao.fim <= agora:
        raise AgendamentoError("A promoção já terminou; ajuste as datas antes de aprovar.")

    # Se o início já passou, posta assim que possível.
    horario = max(promocao.inicio, agora)
    for rede in Postagem.Rede.values:
        Postagem.objects.get_or_create(
            promocao=promocao,
            rede=rede,
            defaults={"agendada_para": horario},
        )
    promocao.status = Promocao.Status.AGENDADA
    promocao.save(update_fields=["status"])
    return promocao


def desagendar_promocao(promocao):
    """Apaga as postagens que ainda não foram ao ar (usado quando a promoção é editada)."""
    promocao.postagens.exclude(status=Postagem.Status.PUBLICADA).delete()


def postagens_na_hora(agora=None):
    """Postagens que já passaram do horário e ainda não foram ao ar."""
    agora = agora or timezone.now()
    return Postagem.objects.filter(
        status=Postagem.Status.PENDENTE,
        agendada_para__lte=agora,
        promocao__status=Promocao.Status.AGENDADA,
    ).select_related("promocao__comercio")


def atualizar_status_promocao(promocao):
    """Marca a promoção como Publicada quando todas as postagens dela foram ao ar."""
    if promocao.status != Promocao.Status.AGENDADA:
        return
    postagens = list(promocao.postagens.all())
    if postagens and all(p.status == Postagem.Status.PUBLICADA for p in postagens):
        promocao.status = Promocao.Status.PUBLICADA
        promocao.save(update_fields=["status"])


@transaction.atomic
def marcar_postagem_publicada(postagem, agora=None):
    if postagem.status != Postagem.Status.PENDENTE:
        raise AgendamentoError("Essa postagem não está pendente.")
    if postagem.promocao.status == Promocao.Status.ENCERRADA:
        raise AgendamentoError("A promoção já foi encerrada.")
    postagem.status = Postagem.Status.PUBLICADA
    postagem.publicada_em = agora or timezone.now()
    postagem.erro = ""
    postagem.save(update_fields=["status", "publicada_em", "erro"])
    atualizar_status_promocao(postagem.promocao)


@transaction.atomic
def encerrar_vencidas(agora=None):
    """Encerra promoções que passaram do fim. Postagens que não saíram ficam com erro."""
    agora = agora or timezone.now()
    vencidas = Promocao.objects.filter(fim__lte=agora).exclude(status=Promocao.Status.ENCERRADA)
    ids = list(vencidas.values_list("pk", flat=True))
    Postagem.objects.filter(promocao_id__in=ids, status=Postagem.Status.PENDENTE).update(
        status=Postagem.Status.ERRO,
        erro="A promoção terminou antes de a postagem ser publicada.",
    )
    Promocao.objects.filter(pk__in=ids).update(status=Promocao.Status.ENCERRADA)
    return len(ids)


def processar(agora=None):
    """Rodada do agendador. Chamada pelo comando `processar_agendamentos`."""
    agora = agora or timezone.now()

    encerradas = encerrar_vencidas(agora)

    # Rede de segurança: promoções aprovadas por fora do painel (ex.: no Admin).
    agendadas = 0
    for promocao in Promocao.objects.filter(status=Promocao.Status.APROVADA):
        agendar_promocao(promocao, agora)
        agendadas += 1

    # Fase 4: aqui entra a publicação automática pela API da Meta.
    # Por enquanto só contamos o que está na hora de postar à mão.
    na_hora = postagens_na_hora(agora).count()

    return {"encerradas": encerradas, "agendadas": agendadas, "na_hora": na_hora}
