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


class VitrineTests(Base):
    def setUp(self):
        super().setUp()
        self.mercado_m = self.comercio("Mercado Maurilândia", whatsapp="(64) 99999-1234", instagram="@mercadom")
        self.farmacia_t = self.comercio("Farmácia Turvelândia", categoria=self.farmacia, cidade=Cidade.TURVELANDIA)
        self.arroz = self.promocao(self.mercado_m, "Arroz 5kg", preco=Decimal("22.90"), preco_de=Decimal("27.50"))
        self.remedio = self.promocao(self.farmacia_t, "Vitamina C", destaque=True)
        self.vencida = self.promocao(
            self.mercado_m, "Feijão vencido",
            inicio=self.agora - timedelta(days=3), fim=self.agora - timedelta(minutes=5),
        )

    def get(self, **params):
        return self.client.get(reverse("inicio"), params)

    def test_inicio_publico_mostra_so_promocoes_ativas(self):
        resp = self.get()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Arroz 5kg")
        self.assertContains(resp, "Vitamina C")
        self.assertNotContains(resp, "Feijão vencido")
        self.assertContains(resp, "2 promoções valendo agora")

    def test_preco_formatado(self):
        resp = self.get()
        self.assertContains(resp, "R$ 22,90")
        self.assertContains(resp, "R$ 27,50")

    def test_destaque_vem_primeiro_na_pagina(self):
        html = self.get().content.decode()
        self.assertLess(html.index("Vitamina C"), html.index("Arroz 5kg"))
        self.assertIn("Destaque", html)

    def test_filtro_por_cidade(self):
        resp = self.get(cidade="turvelandia")
        self.assertContains(resp, "Vitamina C")
        self.assertNotContains(resp, "Arroz 5kg")

    def test_filtro_por_categoria(self):
        resp = self.get(categoria="mercado")
        self.assertContains(resp, "Arroz 5kg")
        self.assertNotContains(resp, "Vitamina C")

    def test_filtros_combinados_sem_resultado(self):
        resp = self.get(cidade="turvelandia", categoria="mercado")
        self.assertContains(resp, "Nenhuma promoção com esses filtros agora.")

    def test_so_mostra_categorias_com_promocao(self):
        resp = self.get()
        self.assertContains(resp, "categoria=mercado")
        self.assertContains(resp, "categoria=farmacia")
        self.assertNotContains(resp, "categoria=padaria")
        # Em Turvelândia não tem mercado com promoção
        resp = self.get(cidade="turvelandia")
        self.assertNotContains(resp, "categoria=mercado")

    def test_filtro_invalido_e_ignorado(self):
        resp = self.get(cidade="goiania", categoria="nao-existe")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "2 promoções valendo agora")

    def test_vitrine_vazia(self):
        Promocao.objects.all().delete()
        self.assertContains(self.get(), "Nenhuma promoção no ar agora.")

    def test_pagina_do_comercio(self):
        resp = self.client.get(reverse("comercio", args=[self.mercado_m.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Mercado Maurilândia")
        self.assertContains(resp, "Arroz 5kg")
        self.assertNotContains(resp, "Feijão vencido")
        self.assertContains(resp, "https://wa.me/5564999991234?text=")
        self.assertContains(resp, "Quero essa promoção")
        self.assertContains(resp, "https://instagram.com/mercadom")
        self.assertContains(resp, f'id="promo-{self.arroz.pk}"')

    def test_comercio_sem_whatsapp_nao_mostra_botao(self):
        resp = self.client.get(reverse("comercio", args=[self.farmacia_t.slug]))
        self.assertNotContains(resp, "wa.me")

    def test_comercio_inativo_ou_inexistente_da_404(self):
        self.mercado_m.ativo = False
        self.mercado_m.save()
        self.assertEqual(self.client.get(reverse("comercio", args=[self.mercado_m.slug])).status_code, 404)
        resp = self.client.get(reverse("comercio", args=["nao-existe"]))
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, "Não achamos essa página.", status_code=404)
        self.assertNotContains(self.get(), "Arroz 5kg")

    def test_card_leva_para_a_promocao_na_pagina_do_comercio(self):
        resp = self.get()
        self.assertContains(resp, f"{self.mercado_m.get_absolute_url()}#promo-{self.arroz.pk}")

    def test_tags_para_compartilhar_no_whatsapp(self):
        resp = self.client.get(reverse("comercio", args=[self.mercado_m.slug]))
        self.assertContains(resp, 'property="og:title" content="Mercado Maurilândia no Achou Promo"')
        self.assertContains(resp, 'property="og:image" content="http://testserver/media/promocoes/')

    def test_nao_precisa_de_login(self):
        self.client.logout()
        self.assertEqual(self.get().status_code, 200)
