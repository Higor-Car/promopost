"""Contagem de acessos para mostrar resultado aos comércios.

Guarda só contadores por dia (quantas vezes), nunca IP ou dados de quem acessou.
Não conta robôs (Google, prévia de link do WhatsApp/Facebook etc.) nem a equipe logada no admin.
Se der qualquer erro ao contar, a página continua funcionando normalmente.
"""

import logging
import re

from django.db import DatabaseError, connection
from django.utils import timezone

from .models import MetricaDiaria

log = logging.getLogger(__name__)

ROBOS = re.compile(
    r"bot|crawl|spider|slurp|facebookexternalhit|facebot|whatsapp|telegram|preview|"
    r"curl|wget|python|httpclient|headless|lighthouse|monitor|uptime",
    re.IGNORECASE,
)

Tipo = MetricaDiaria.Tipo


def deve_contar(request):
    if request.method != "GET":
        return False
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated and usuario.is_staff:
        return False
    agente = request.META.get("HTTP_USER_AGENT", "")
    return bool(agente) and not ROBOS.search(agente)


def _chave(comercio_id, promocao_id, tipo):
    return f"c{comercio_id}-p{promocao_id or 0}-{tipo}"


def registrar_varios(request, tipo, pares):
    """Soma 1 para cada (comercio_id, promocao_id) em `pares`, no dia de hoje."""
    if not pares or not deve_contar(request):
        return
    dia = timezone.localdate()
    tabela = connection.ops.quote_name(MetricaDiaria._meta.db_table)
    linhas = [
        (dia, _chave(comercio_id, promocao_id, tipo), comercio_id, promocao_id, tipo)
        for comercio_id, promocao_id in pares
    ]
    sql = (
        f"INSERT INTO {tabela} (dia, chave, comercio_id, promocao_id, tipo, total) "
        "VALUES (%s, %s, %s, %s, %s, 1) "
        "ON CONFLICT (dia, chave) DO UPDATE SET total = total + 1"
    )
    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, linhas)
    except DatabaseError:
        log.exception("Falha ao registrar métrica %s", tipo)


def registrar(request, tipo, comercio_id, promocao_id=None):
    registrar_varios(request, tipo, [(comercio_id, promocao_id)])
