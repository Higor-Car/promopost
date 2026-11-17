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
