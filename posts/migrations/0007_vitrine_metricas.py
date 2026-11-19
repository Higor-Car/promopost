import secrets

import django.db.models.deletion
from django.db import migrations, models

import posts.models

ICONES = {
    "mercado": "🛒",
    "acougue": "🥩",
    "padaria": "🥖",
    "farmacia": "💊",
    "restaurante-e-lanchonete": "🍔",
    "roupas-e-calcados": "👕",
    "beleza": "💅",
    "casa-e-construcao": "🏠",
    "pet": "🐾",
    "servicos": "🛠️",
    "outros": "🏷️",
}


def colocar_icones(apps, schema_editor):
    Categoria = apps.get_model("posts", "Categoria")
    for slug, icone in ICONES.items():
        Categoria.objects.filter(slug=slug, icone="").update(icone=icone)


def gerar_tokens(apps, schema_editor):
    Comercio = apps.get_model("posts", "Comercio")
    for comercio in Comercio.objects.filter(token_resultado__isnull=True):
        comercio.token_resultado = secrets.token_urlsafe(16)
        comercio.save(update_fields=["token_resultado"])


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0006_help_text_slug"),
    ]

    operations = [
        migrations.AddField(
            model_name="categoria",
            name="icone",
            field=models.CharField(blank=True, help_text="Um emoji. Ex.: 🛒", max_length=8, verbose_name="ícone"),
        ),
        migrations.RunPython(colocar_icones, migrations.RunPython.noop),

        # Um token diferente por comércio (um default simples daria o mesmo para todos).
        migrations.AddField(
            model_name="comercio",
            name="token_resultado",
            field=models.CharField(max_length=32, null=True, editable=False),
        ),
        migrations.RunPython(gerar_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="comercio",
            name="token_resultado",
            field=models.CharField(
                default=posts.models.novo_token, editable=False, max_length=32, unique=True,
                verbose_name="código do link de resultado",
            ),
        ),

        migrations.CreateModel(
            name="MetricaDiaria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dia", models.DateField()),
                ("chave", models.CharField(editable=False, max_length=60)),
                ("tipo", models.CharField(
                    choices=[
                        ("impressao", "Apareceu na vitrine"),
                        ("visita_promocao", "Abriu a promoção"),
                        ("visita_comercio", "Visitou a página da loja"),
                        ("whatsapp", "Clicou no WhatsApp"),
                        ("instagram", "Clicou no Instagram"),
                        ("mapa", "Clicou em Como chegar"),
                        ("qr", "Chegou pelo QR code"),
                    ],
                    max_length=20,
                )),
                ("total", models.PositiveIntegerField(default=0)),
                ("comercio", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="metricas", to="posts.comercio",
                )),
                ("promocao", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="metricas", to="posts.promocao",
                )),
            ],
            options={
                "verbose_name": "métrica diária",
                "verbose_name_plural": "métricas diárias",
                "indexes": [models.Index(fields=["comercio", "dia"], name="posts_metri_comerci_f1424a_idx")],
                "constraints": [models.UniqueConstraint(fields=("dia", "chave"), name="metrica_unica_por_dia")],
            },
        ),
    ]
