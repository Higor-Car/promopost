import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.utils.text import slugify

CATEGORIAS = [
    ("Mercado", "mercado"),
    ("Açougue", "acougue"),
    ("Padaria", "padaria"),
    ("Farmácia", "farmacia"),
    ("Restaurante e lanchonete", "restaurante-e-lanchonete"),
    ("Roupas e calçados", "roupas-e-calcados"),
    ("Beleza", "beleza"),
    ("Casa e construção", "casa-e-construcao"),
    ("Pet", "pet"),
    ("Serviços", "servicos"),
    ("Outros", "outros"),
]

CIDADES = {"maurilândia": "maurilandia", "maurilandia": "maurilandia",
           "turvelândia": "turvelandia", "turvelandia": "turvelandia"}


def criar_categorias(apps, schema_editor):
    Categoria = apps.get_model("posts", "Categoria")
    for ordem, (nome, slug) in enumerate(CATEGORIAS):
        Categoria.objects.get_or_create(slug=slug, defaults={"nome": nome, "ordem": ordem * 10})


def preencher_comercios(apps, schema_editor):
    Categoria = apps.get_model("posts", "Categoria")
    Comercio = apps.get_model("posts", "Comercio")
    outros = Categoria.objects.get(slug="outros")
    usados = set()
    for comercio in Comercio.objects.all():
        base = slugify(comercio.nome)[:130] or "comercio"
        slug, n = base, 2
        while slug in usados:
            slug, n = f"{base}-{n}", n + 1
        usados.add(slug)
        comercio.slug = slug
        comercio.categoria = outros
        comercio.cidade = CIDADES.get(comercio.cidade.strip().lower(), "maurilandia")
        comercio.save(update_fields=["slug", "categoria", "cidade"])


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0003_remove_postagem"),
    ]

    operations = [
        # Categorias
        migrations.CreateModel(
            name="Categoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=60, unique=True)),
                ("slug", models.SlugField(help_text="Usado no endereço do filtro.", max_length=60, unique=True)),
                ("ordem", models.PositiveSmallIntegerField(default=0, help_text="Menor aparece primeiro.")),
            ],
            options={
                "verbose_name": "categoria",
                "verbose_name_plural": "categorias",
                "ordering": ["ordem", "nome"],
            },
        ),
        migrations.RunPython(criar_categorias, migrations.RunPython.noop),

        # Comércio: slug e categoria entram vazios, são preenchidos e depois ficam obrigatórios
        migrations.AddField(
            model_name="comercio",
            name="slug",
            field=models.SlugField(max_length=140, default="", blank=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="comercio",
            name="categoria",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="comercios", to="posts.categoria",
            ),
        ),
        migrations.RunPython(preencher_comercios, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="comercio",
            name="slug",
            field=models.SlugField(
                help_text="Endereço da página: achoupromo.com.br/c/<slug>/", max_length=140, unique=True
            ),
        ),
        migrations.AlterField(
            model_name="comercio",
            name="categoria",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="comercios", to="posts.categoria"
            ),
        ),
        migrations.AlterField(
            model_name="comercio",
            name="cidade",
            field=models.CharField(
                choices=[("maurilandia", "Maurilândia"), ("turvelandia", "Turvelândia")],
                default="maurilandia", max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="comercio",
            name="endereco",
            field=models.CharField(blank=True, max_length=200, verbose_name="endereço"),
        ),
        migrations.AddField(
            model_name="comercio",
            name="descricao",
            field=models.TextField(blank=True, verbose_name="descrição"),
        ),
        migrations.AddField(
            model_name="comercio",
            name="logo",
            field=models.ImageField(blank=True, upload_to="comercios/"),
        ),
        migrations.AlterField(
            model_name="comercio",
            name="whatsapp",
            field=models.CharField(blank=True, help_text="Com DDD. Ex.: (64) 99999-1234", max_length=20),
        ),
        migrations.AlterField(
            model_name="comercio",
            name="ativo",
            field=models.BooleanField(default=True, help_text="Desmarque para tirar o comércio da vitrine."),
        ),

        # Promoção: sai o fluxo de status, entram preço, destaque e validade
        migrations.RenameField(model_name="promocao", old_name="legenda", new_name="descricao"),
        migrations.AlterField(
            model_name="promocao",
            name="descricao",
            field=models.TextField(blank=True, verbose_name="descrição"),
        ),
        migrations.RemoveField(model_name="promocao", name="status"),
        migrations.AlterField(
            model_name="promocao",
            name="titulo",
            field=models.CharField(max_length=150, verbose_name="título"),
        ),
        migrations.AddField(
            model_name="promocao",
            name="preco",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Opcional. Preço da promoção.",
                max_digits=9, null=True, verbose_name="preço",
            ),
        ),
        migrations.AddField(
            model_name="promocao",
            name="preco_de",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text='Opcional. Aparece riscado ("de R$ X por R$ Y").',
                max_digits=9, null=True, verbose_name="preço antes",
            ),
        ),
        migrations.AddField(
            model_name="promocao",
            name="destaque",
            field=models.BooleanField(default=False, help_text="Aparece primeiro, com selo de destaque."),
        ),
        migrations.AlterField(
            model_name="promocao",
            name="inicio",
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name="aparece a partir de"),
        ),
        migrations.AlterField(
            model_name="promocao",
            name="fim",
            field=models.DateTimeField(help_text="Depois desse horário some da vitrine.", verbose_name="válida até"),
        ),
        migrations.AlterModelOptions(
            name="promocao",
            options={
                "ordering": ["-destaque", "fim"],
                "verbose_name": "promoção",
                "verbose_name_plural": "promoções",
            },
        ),
    ]
