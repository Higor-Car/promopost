import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from posts.agendamento import processar


class Command(BaseCommand):
    help = (
        "Encerra promoções vencidas, agenda as aprovadas e mostra quantas postagens "
        "estão na hora de publicar. Rode de 5 em 5 minutos (Agendador de Tarefas ou cron)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--a-cada",
            type=int,
            metavar="MINUTOS",
            help="Fica rodando sem parar, repetindo a cada N minutos (Ctrl+C para sair).",
        )

    def handle(self, *args, a_cada=None, **options):
        while True:
            resultado = processar()
            agora = timezone.localtime().strftime("%d/%m/%Y %H:%M")
            self.stdout.write(
                f"[{agora}] encerradas: {resultado['encerradas']} · "
                f"agendadas: {resultado['agendadas']} · "
                f"na hora de postar: {resultado['na_hora']}"
            )
            if not a_cada:
                break
            time.sleep(a_cada * 60)
