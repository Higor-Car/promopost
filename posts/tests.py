import io
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Categoria, Cidade, Comercio, Promocao

MEDIA_TESTE = tempfile.mkdtemp(prefix="achoupromo_test_media_")


def imagem_falsa(nome="promo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA_TESTE)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TESTE, ignore_errors=True)

    def setUp(self):
        self.agora = timezone.now()
        self.mercado = Categoria.objects.get(slug="mercado")
        self.farmacia = Categoria.objects.get(slug="farmacia")

    def comercio(self, nome="Mercado Teste", **extra):
        dados = {"nome": nome, "categoria": self.mercado, "cidade": Cidade.MAURILANDIA}
        dados.update(extra)
        return Comercio.objects.create(**dados)

    def promocao(self, comercio, titulo="Arroz 5kg", **extra):
        dados = {
            "comercio": comercio,
            "titulo": titulo,
            "imagem": imagem_falsa(),
            "inicio": self.agora - timedelta(hours=1),
            "fim": self.agora + timedelta(days=2),
        }
        dados.update(extra)
        return Promocao.objects.create(**dados)


class ModelTests(Base):
    def test_categorias_iniciais_criadas_pela_migracao(self):
        self.assertTrue(Categoria.objects.filter(slug="outros").exists())
        self.assertGreaterEqual(Categoria.objects.count(), 10)

    def test_slug_automatico(self):
        self.assertEqual(self.comercio("Açougue do Zé").slug, "acougue-do-ze")

    def test_whatsapp_normalizado(self):
        casos = {
            "(64) 99999-1234": "5564999991234",
            "64 3555-1234": "556435551234",
            "+55 64 99999-1234": "5564999991234",
            "": "",
        }
        for digitado, esperado in casos.items():
            self.assertEqual(Comercio(whatsapp=digitado).whatsapp_numero, esperado, digitado)

    def test_link_whatsapp_com_mensagem(self):
        c = Comercio(whatsapp="(64) 99999-1234")
        self.assertEqual(
            c.link_whatsapp("Olá, tudo bem?"),
            "https://wa.me/5564999991234?text=Ol%C3%A1%2C%20tudo%20bem%3F",
        )
        self.assertEqual(Comercio(whatsapp="").link_whatsapp("oi"), "")

    def test_instagram_usuario(self):
        for digitado in ("@loja", "loja", "https://instagram.com/loja"):
            self.assertEqual(Comercio(instagram=digitado).instagram_usuario, "loja")

    def test_ativas_respeita_validade_e_comercio_ativo(self):
        loja = self.comercio()
        no_ar = self.promocao(loja, "No ar")
        self.promocao(loja, "Vencida", inicio=self.agora - timedelta(days=3), fim=self.agora - timedelta(minutes=1))
        self.promocao(loja, "Futura", inicio=self.agora + timedelta(hours=1))
        inativa = self.comercio("Loja fechada", ativo=False)
        self.promocao(inativa, "De loja inativa")
        self.assertEqual(list(Promocao.objects.ativas()), [no_ar])

    def test_destaque_vem_primeiro(self):
        loja = self.comercio()
        comum = self.promocao(loja, "Comum", fim=self.agora + timedelta(hours=2))
        destaque = self.promocao(loja, "Destaque", fim=self.agora + timedelta(days=5), destaque=True)
        self.assertEqual(list(Promocao.objects.ativas()), [destaque, comum])

    def test_validacao_validade_e_precos(self):
        loja = self.comercio()
        p = Promocao(comercio=loja, titulo="X", inicio=self.agora, fim=self.agora - timedelta(hours=1))
        with self.assertRaises(ValidationError) as erro:
            p.clean()
        self.assertIn("fim", erro.exception.message_dict)

        p = Promocao(
            comercio=loja, titulo="X", inicio=self.agora, fim=self.agora + timedelta(days=1),
            preco=Decimal("10"), preco_de=Decimal("9"),
        )
        with self.assertRaises(ValidationError) as erro:
            p.clean()
        self.assertIn("preco_de", erro.exception.message_dict)


class AdminTests(Base):
    def setUp(self):
        super().setUp()
        admin = get_user_model().objects.create_superuser("admin", password="senha-teste-123")
        self.client.force_login(admin)
        self.loja = self.comercio()
        self.promo = self.promocao(self.loja)

    def test_telas_do_admin_abrem(self):
        urls = [
            reverse("admin:posts_comercio_changelist"),
            reverse("admin:posts_comercio_change", args=[self.loja.pk]),
            reverse("admin:posts_comercio_add"),
            reverse("admin:posts_categoria_changelist"),
            reverse("admin:posts_promocao_changelist"),
            reverse("admin:posts_promocao_changelist") + "?situacao=no_ar",
            reverse("admin:posts_promocao_changelist") + "?situacao=vencida",
            reverse("admin:posts_promocao_change", args=[self.promo.pk]),
            reverse("admin:posts_promocao_add"),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_acao_encerrar_agora(self):
        self.client.post(
            reverse("admin:posts_promocao_changelist"),
            {"action": "encerrar_agora", "_selected_action": [self.promo.pk]},
        )
        self.assertFalse(Promocao.objects.ativas().exists())

    def test_excluir_pelo_admin(self):
        self.client.post(reverse("admin:posts_promocao_delete", args=[self.promo.pk]), {"post": "yes"})
        self.assertFalse(Promocao.objects.filter(pk=self.promo.pk).exists())
