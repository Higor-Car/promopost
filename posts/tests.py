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


CELULAR = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"


class VitrineTests(Base):
    def setUp(self):
        super().setUp()
        self.mercado_m = self.comercio(
            "Mercado Maurilândia", whatsapp="(64) 99999-1234", instagram="@mercadom",
            endereco="Av. Central, 120",
        )
        self.farmacia_t = self.comercio("Farmácia Turvelândia", categoria=self.farmacia, cidade=Cidade.TURVELANDIA)
        self.arroz = self.promocao(
            self.mercado_m, "Arroz 5kg", preco=Decimal("22.90"), preco_de=Decimal("27.50"),
            descricao="Tipo 1, pacote de cinco quilos",
        )
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
        self.assertEqual(resp.context["total"], 2)
        self.assertContains(resp, "2 ofertas valendo agora")
        self.assertContains(resp, "em um só lugar")
        self.assertNotContains(resp, "num lugar só")

    def test_preco_e_desconto(self):
        resp = self.get()
        self.assertContains(resp, "R$ 22,90")
        self.assertContains(resp, "R$ 27,50")
        self.assertContains(resp, "-17%")
        self.assertEqual(self.arroz.desconto, 17)
        self.assertIsNone(self.remedio.desconto)

    def test_destaque_aparece_na_secao_de_destaques(self):
        html = self.get().content.decode()
        self.assertIn("Em destaque", html)
        self.assertLess(html.index("Vitamina C"), html.index("Arroz 5kg"))

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
        self.assertContains(resp, "Tente outra palavra, outra categoria ou outra cidade.")

    def test_so_mostra_categorias_com_promocao_sem_emoji(self):
        resp = self.get()
        self.assertContains(resp, "categoria=mercado")
        self.assertContains(resp, "categoria=farmacia")
        self.assertNotContains(resp, "categoria=padaria")
        html = resp.content.decode()
        emojis = [c for c in html if 0x1F000 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF]
        self.assertEqual(emojis, [])
        resp = self.get(cidade="turvelandia")
        self.assertNotContains(resp, "categoria=mercado")

    def test_filtro_invalido_e_ignorado(self):
        resp = self.get(cidade="goiania", categoria="nao-existe")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Arroz 5kg")
        self.assertContains(resp, "Vitamina C")

    def test_busca_sem_acento_e_por_loja(self):
        resp = self.get(q="ARROZ cinco")
        self.assertContains(resp, "Arroz 5kg")
        self.assertNotContains(resp, "Vitamina C")
        self.assertContains(resp, "1 resultado para")
        # "farmacia" sem acento acha pelo nome da loja e da categoria
        resp = self.get(q="farmacia")
        self.assertContains(resp, "Vitamina C")
        self.assertNotContains(resp, "Arroz 5kg")

    def test_busca_sem_resultado(self):
        resp = self.get(q="televisão")
        self.assertContains(resp, "Nada por aqui")

    def test_vitrine_vazia(self):
        Promocao.objects.all().delete()
        self.assertContains(self.get(), "Nenhuma promoção no ar agora")

    def test_card_leva_para_a_pagina_da_promocao(self):
        self.assertContains(self.get(), f'href="/p/{self.arroz.pk}/"')

    def test_pagina_do_comercio(self):
        resp = self.client.get(reverse("comercio", args=[self.mercado_m.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Mercado Maurilândia")
        self.assertContains(resp, "Arroz 5kg")
        self.assertNotContains(resp, "Feijão vencido")
        self.assertContains(resp, reverse("ir_whatsapp_comercio", args=[self.mercado_m.slug]))
        self.assertContains(resp, reverse("ir_instagram", args=[self.mercado_m.slug]))
        self.assertContains(resp, reverse("ir_mapa", args=[self.mercado_m.slug]))
        self.assertContains(resp, "Compartilhar")

    def test_comercio_sem_whatsapp_nem_endereco_nao_mostra_botoes(self):
        resp = self.client.get(reverse("comercio", args=[self.farmacia_t.slug]))
        self.assertNotContains(resp, "Chamar no WhatsApp")
        self.assertNotContains(resp, "Como chegar")
        self.assertNotContains(resp, "/ir/instagram/")

    def test_pagina_da_promocao(self):
        resp = self.client.get(reverse("promocao", args=[self.arroz.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<h1>Arroz 5kg</h1>", html=True)
        self.assertContains(resp, "Quero essa promoção")
        self.assertContains(resp, reverse("ir_whatsapp_promocao", args=[self.arroz.pk]))
        self.assertContains(resp, "Economia de 17%")
        self.assertContains(resp, 'property="og:title" content="Arroz 5kg — R$ 22,90"')
        self.assertContains(resp, 'property="og:image" content="http://testserver/media/promocoes/')
        self.assertContains(resp, "https://wa.me/?text=")

    def test_promocao_vencida_mostra_aviso(self):
        resp = self.client.get(reverse("promocao", args=[self.vencida.pk]))
        self.assertEqual(resp.status_code, 410)
        self.assertContains(resp, "não está mais valendo", status_code=410)
        self.assertContains(resp, "Arroz 5kg", status_code=410)

    def test_comercio_inativo_ou_inexistente_da_404(self):
        self.mercado_m.ativo = False
        self.mercado_m.save()
        self.assertEqual(self.client.get(reverse("comercio", args=[self.mercado_m.slug])).status_code, 404)
        self.assertEqual(self.client.get(reverse("promocao", args=[self.arroz.pk])).status_code, 404)
        resp = self.client.get(reverse("comercio", args=["nao-existe"]))
        self.assertContains(resp, "Não achamos essa página.", status_code=404)
        self.assertNotContains(self.get(), "Arroz 5kg")

    def test_saidas_redirecionam_para_o_destino(self):
        resp = self.client.get(reverse("ir_whatsapp_promocao", args=[self.arroz.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("https://wa.me/5564999991234?text="))
        self.assertIn("Arroz%205kg", resp["Location"])
        resp = self.client.get(reverse("ir_instagram", args=[self.mercado_m.slug]))
        self.assertEqual(resp["Location"], "https://instagram.com/mercadom")
        resp = self.client.get(reverse("ir_mapa", args=[self.mercado_m.slug]))
        self.assertTrue(resp["Location"].startswith("https://www.google.com/maps/search/"))
        # Loja sem WhatsApp: não existe saída
        self.assertEqual(self.client.get(reverse("ir_whatsapp_comercio", args=[self.farmacia_t.slug])).status_code, 404)

    def test_robots(self):
        resp = self.client.get("/robots.txt")
        self.assertContains(resp, "Disallow: /resultado/")
        self.assertEqual(resp["Content-Type"], "text/plain")

    def test_nao_precisa_de_login(self):
        self.client.logout()
        self.assertEqual(self.get().status_code, 200)


class EstruturaTests(Base):
    """Menu, páginas Lojas/Categorias/Para lojistas e abas da página da loja."""

    def setUp(self):
        super().setUp()
        self.loja1 = self.comercio(
            "Mercado Um", whatsapp="64999991234", instagram="@mercadoum", endereco="Rua 1, 10",
            horario="Seg a sex: 7h às 19h\nSáb: 7h às 13h", descricao="Hortifrúti todo dia.",
        )
        self.farmacia_t = self.comercio("Farmácia Dois", categoria=self.farmacia, cidade=Cidade.TURVELANDIA)
        self.sem_oferta = self.comercio("Loja Sem Oferta")
        self.arroz = self.promocao(self.loja1, "Arroz 5kg")
        hoje_noite = timezone.localtime().replace(hour=23, minute=59, second=0, microsecond=0)
        self.pao = self.promocao(self.loja1, "Pão de hoje", fim=max(hoje_noite, self.agora + timedelta(minutes=30)))
        self.remedio = self.promocao(self.farmacia_t, "Vitamina C", destaque=True)

    def test_menu_em_todas_as_paginas(self):
        for url in (reverse("inicio"), reverse("lojas"), reverse("categorias"), reverse("para_lojistas"),
                    self.loja1.get_absolute_url(), self.arroz.get_absolute_url()):
            resp = self.client.get(url)
            self.assertContains(resp, 'class="menu-baixo"', msg_prefix=url)
            self.assertContains(resp, reverse("para_lojistas"), msg_prefix=url)

    def test_menu_marca_a_pagina_atual(self):
        resp = self.client.get(reverse("lojas"))
        self.assertContains(resp, f'href="{reverse("lojas")}" class="ativo" aria-current="page"')

    def test_inicio_tem_secoes(self):
        resp = self.client.get(reverse("inicio"))
        self.assertContains(resp, "Em destaque")
        self.assertContains(resp, "Lojas parceiras")
        self.assertContains(resp, "Tem um comércio na cidade?")
        self.assertContains(resp, "data-suave")  # cidade/categoria trocam sem recarregar
        if self.pao.acaba_hoje:
            self.assertContains(resp, "Acaba hoje")
            self.assertIn(self.pao, resp.context["acabando"])
            self.assertNotIn(self.pao, resp.context["promocoes"])
        # Loja sem oferta não aparece na faixa de lojas do início
        self.assertNotIn(self.sem_oferta, resp.context["lojas"])

    def test_pagina_lojas(self):
        resp = self.client.get(reverse("lojas"))
        self.assertContains(resp, "Mercado Um")
        self.assertContains(resp, "Loja Sem Oferta")
        self.assertContains(resp, "2 ofertas agora")
        self.assertContains(resp, "Sem oferta agora")
        nomes = [loja.nome for loja in resp.context["lojas"]]
        self.assertEqual(nomes[-1], "Loja Sem Oferta")  # lojas com oferta primeiro
        resp = self.client.get(reverse("lojas"), {"cidade": "turvelandia"})
        self.assertEqual([loja.nome for loja in resp.context["lojas"]], ["Farmácia Dois"])
        resp = self.client.get(reverse("lojas"), {"categoria": "farmacia"})
        self.assertEqual([loja.nome for loja in resp.context["lojas"]], ["Farmácia Dois"])

    def test_pagina_categorias(self):
        resp = self.client.get(reverse("categorias"))
        self.assertContains(resp, "Mercado")
        self.assertContains(resp, "?categoria=mercado")
        primeira = resp.context["categorias"][0]
        self.assertGreater(primeira.total, 0)  # categorias com oferta primeiro
        # Categorias sem loja nem oferta não aparecem
        self.assertNotContains(resp, "Roupas e calçados")
        self.assertNotContains(resp, "?categoria=pet")

    def test_inicio_mostra_no_maximo_6_categorias(self):
        slugs = ["padaria", "acougue", "pet", "beleza", "servicos", "outros", "casa-e-construcao"]
        for i, slug in enumerate(slugs):
            loja = self.comercio(f"Loja {slug}", categoria=Categoria.objects.get(slug=slug))
            for _ in range(i + 1):
                self.promocao(loja, f"Oferta {slug}")
        resp = self.client.get(reverse("inicio"))
        self.assertEqual(len(resp.context["categorias"]), 6)
        self.assertTrue(resp.context["mais_categorias"])
        self.assertContains(resp, f'href="{reverse("categorias")}">Mais</a>')
        # a categoria escolhida aparece mesmo que não esteja entre as 6 com mais ofertas
        resp = self.client.get(reverse("inicio"), {"categoria": "farmacia"})
        self.assertIn("farmacia", [c.slug for c in resp.context["categorias"]])

    def test_pagina_para_lojistas(self):
        resp = self.client.get(reverse("para_lojistas"))
        self.assertContains(resp, "O que sua loja ganha")
        self.assertContains(resp, "Clientes no seu WhatsApp")
        self.assertContains(resp, "Dúvidas")
        self.assertContains(resp, "Como funciona")
        self.assertFalse(resp.context["mostrar_numeros"])  # poucos números ainda
        self.assertNotContains(resp, "lojas parceiras</span>")

    @override_settings(CONTATO_WHATSAPP="5564988887777")
    def test_para_lojistas_com_contato(self):
        resp = self.client.get(reverse("para_lojistas"))
        self.assertContains(resp, "https://wa.me/5564988887777?text=")
        self.assertContains(resp, "Quero anunciar")

    def test_loja_aba_promocoes_por_padrao(self):
        resp = self.client.get(self.loja1.get_absolute_url())
        self.assertEqual(resp.context["aba"], "promocoes")
        self.assertContains(resp, 'id="painel-info" role="tabpanel" aria-labelledby="aba-info" hidden')
        self.assertContains(resp, "Arroz 5kg")

    def test_loja_aba_informacoes(self):
        resp = self.client.get(self.loja1.get_absolute_url(), {"aba": "info"})
        self.assertEqual(resp.context["aba"], "info")
        self.assertContains(resp, 'id="painel-promocoes" role="tabpanel" aria-labelledby="aba-promocoes" hidden')
        self.assertContains(resp, "Horário de funcionamento")
        self.assertContains(resp, "Sáb: 7h às 13h")
        self.assertContains(resp, "(64) 99999-1234")
        self.assertContains(resp, "Hortifrúti todo dia.")

    def test_capa_da_loja(self):
        resp = self.client.get(self.loja1.get_absolute_url())
        self.assertNotContains(resp, "/media/comercios/capas/")  # sem foto: só a cor
        self.assertContains(resp, "--cor:")
        self.loja1.capa = imagem_falsa("capa.png")
        self.loja1.save()
        resp = self.client.get(self.loja1.get_absolute_url())
        self.assertContains(resp, "/media/comercios/capas/")

    def test_whatsapp_formatado(self):
        self.assertEqual(Comercio(whatsapp="64999991234").whatsapp_formatado, "(64) 99999-1234")
        self.assertEqual(Comercio(whatsapp="6435551234").whatsapp_formatado, "(64) 3555-1234")

    def test_arquivos_estaticos_do_visual(self):
        resp = self.client.get(reverse("inicio"))
        self.assertContains(resp, "vitrine/site.css")
        self.assertContains(resp, "vitrine/site.js")


class MetricasTests(Base):
    def setUp(self):
        super().setUp()
        self.loja = self.comercio("Mercado Um", whatsapp="64999991234")
        self.promo = self.promocao(self.loja, "Arroz")
        self.client.defaults["HTTP_USER_AGENT"] = CELULAR

    def total(self, tipo, promocao=None):
        from django.db.models import Sum

        from .models import MetricaDiaria

        qs = MetricaDiaria.objects.filter(comercio=self.loja, tipo=tipo)
        if promocao is not None:
            qs = qs.filter(promocao=promocao)
        return qs.aggregate(n=Sum("total"))["n"] or 0

    def test_conta_visitas_impressoes_cliques_e_qr(self):
        self.client.get(reverse("inicio"))
        self.client.get(reverse("inicio"))
        self.client.get(reverse("comercio", args=[self.loja.slug]) + "?origem=qr")
        self.client.get(reverse("promocao", args=[self.promo.pk]))
        self.client.get(reverse("ir_whatsapp_promocao", args=[self.promo.pk]))
        self.client.get(reverse("ir_whatsapp_comercio", args=[self.loja.slug]))
        self.assertEqual(self.total("impressao", self.promo), 3)  # 2x início + 1x página da loja
        self.assertEqual(self.total("visita_comercio"), 1)
        self.assertEqual(self.total("qr"), 1)
        self.assertEqual(self.total("visita_promocao", self.promo), 1)
        self.assertEqual(self.total("whatsapp"), 2)

    def test_nao_conta_robos_nem_equipe(self):
        self.client.get(reverse("promocao", args=[self.promo.pk]), HTTP_USER_AGENT="WhatsApp/2.23.20.0")
        self.client.get(reverse("promocao", args=[self.promo.pk]), HTTP_USER_AGENT="Googlebot/2.1")
        self.client.get(reverse("promocao", args=[self.promo.pk]), HTTP_USER_AGENT="")
        admin = get_user_model().objects.create_superuser("admin", password="senha-teste-123")
        self.client.force_login(admin)
        self.client.get(reverse("promocao", args=[self.promo.pk]))
        self.assertEqual(self.total("visita_promocao"), 0)

    def test_um_registro_por_dia_somando(self):
        from .models import MetricaDiaria

        for _ in range(5):
            self.client.get(reverse("promocao", args=[self.promo.pk]))
        self.assertEqual(MetricaDiaria.objects.filter(tipo="visita_promocao").count(), 1)
        self.assertEqual(self.total("visita_promocao"), 5)

    def test_metrica_continua_se_a_promocao_for_apagada(self):
        self.client.get(reverse("ir_whatsapp_promocao", args=[self.promo.pk]))
        self.promo.delete()
        self.assertEqual(self.total("whatsapp"), 1)


class ResultadoTests(Base):
    def setUp(self):
        super().setUp()
        self.loja = self.comercio("Mercado Um", whatsapp="64999991234")
        self.outra = self.comercio("Loja Dois")
        self.promo = self.promocao(self.loja, "Arroz da semana")
        self.client.defaults["HTTP_USER_AGENT"] = CELULAR

    def test_tokens_sao_diferentes_e_grandes(self):
        self.assertNotEqual(self.loja.token_resultado, self.outra.token_resultado)
        self.assertGreaterEqual(len(self.loja.token_resultado), 20)

    def test_pagina_mostra_numeros_da_loja(self):
        self.client.get(reverse("promocao", args=[self.promo.pk]))
        self.client.get(reverse("ir_whatsapp_promocao", args=[self.promo.pk]))
        self.client.get(reverse("comercio", args=[self.loja.slug]) + "?origem=qr")
        resp = self.client.get(self.loja.get_resultado_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(resp, "Mercado Um")
        self.assertContains(resp, "Arroz da semana")
        self.assertEqual(resp.context["whatsapp"], 1)
        self.assertEqual(resp.context["visitas"], 2)
        self.assertEqual(resp.context["qr"], 1)
        self.assertEqual(len(resp.context["grafico"]), 30)

    def test_nao_mistura_lojas(self):
        self.client.get(reverse("ir_whatsapp_promocao", args=[self.promo.pk]))
        resp = self.client.get(self.outra.get_resultado_url())
        self.assertEqual(resp.context["whatsapp"], 0)
        self.assertNotContains(resp, "Arroz da semana")

    def test_periodos(self):
        for dias, esperado in (("7", 7), ("90", 90), ("abc", 30), ("1000", 30)):
            resp = self.client.get(self.loja.get_resultado_url(), {"dias": dias})
            self.assertEqual(len(resp.context["grafico"]), esperado)

    def test_token_errado_da_404(self):
        self.assertEqual(self.client.get(reverse("resultado", args=["errado"])).status_code, 404)

    def test_ver_resultado_nao_conta_como_visita(self):
        self.client.get(self.loja.get_resultado_url())
        self.assertFalse(self.loja.metricas.exists())

    def test_novo_link_invalida_o_antigo(self):
        admin = get_user_model().objects.create_superuser("admin", password="senha-teste-123")
        self.client.force_login(admin)
        antigo = self.loja.get_resultado_url()
        self.client.post(
            reverse("admin:posts_comercio_changelist"),
            {"action": "gerar_novo_link_resultado", "_selected_action": [self.loja.pk]},
        )
        self.loja.refresh_from_db()
        self.assertNotEqual(self.loja.get_resultado_url(), antigo)
        self.assertEqual(self.client.get(antigo).status_code, 404)
        self.assertEqual(self.client.get(self.loja.get_resultado_url()).status_code, 200)

    def test_link_aparece_no_admin(self):
        admin = get_user_model().objects.create_superuser("admin", password="senha-teste-123")
        self.client.force_login(admin)
        resp = self.client.get(reverse("admin:posts_comercio_change", args=[self.loja.pk]))
        self.assertContains(resp, self.loja.get_resultado_url())


class ImagemInstagramTests(Base):
    def setUp(self):
        super().setUp()
        admin = get_user_model().objects.create_superuser("admin", password="senha-teste-123")
        self.client.force_login(admin)
        loja = self.comercio("Mercado Um")
        self.promos = [
            self.promocao(loja, f"Promoção número {i} com um nome bem comprido para quebrar linha",
                          preco=Decimal("9.90"), preco_de=Decimal("12.00") if i % 2 else None)
            for i in range(7)
        ]
        self.url = reverse("admin:posts_promocao_imagem_do_dia")

    def test_gera_png_no_tamanho_do_instagram(self):
        resp = self.client.get(self.url, {"png": "1"})
        self.assertEqual(resp["Content-Type"], "image/png")
        im = Image.open(io.BytesIO(resp.content))
        self.assertEqual(im.size, (1080, 1350))

    def test_pagina_de_previa_e_download_em_carrossel(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "Baixar imagem 1")
        self.assertContains(resp, "Baixar imagem 2")
        self.assertContains(resp, "carrossel")
        self.assertEqual(len(resp.context["promocoes"]), 6)
        self.assertEqual([len(i["promocoes"]) for i in resp.context["imagens"]], [3, 3])
        resp = self.client.get(self.url, {"png": "1", "pagina": "2", "baixar": "1"})
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertIn("-2.png", resp["Content-Disposition"])
        self.assertEqual(self.client.get(self.url, {"png": "1", "pagina": "3"}).status_code, 404)

    def test_escolhendo_as_promocoes(self):
        ids = f"{self.promos[0].pk},{self.promos[3].pk}"
        resp = self.client.get(self.url, {"ids": ids})
        self.assertEqual([p.pk for p in resp.context["promocoes"]], [self.promos[0].pk, self.promos[3].pk])
        resp = self.client.get(self.url, {"ids": ids, "png": "1"})
        self.assertEqual(Image.open(io.BytesIO(resp.content)).size, (1080, 1350))

    def test_acao_na_lista(self):
        resp = self.client.post(
            reverse("admin:posts_promocao_changelist"),
            {"action": "imagem_instagram", "_selected_action": [self.promos[1].pk]},
        )
        self.assertContains(resp, f"ids={self.promos[1].pk}")

    def test_sem_promocoes(self):
        Promocao.objects.all().delete()
        self.assertContains(self.client.get(self.url), "Nenhuma promoção no ar agora")
        self.assertEqual(self.client.get(self.url, {"png": "1"}).status_code, 404)

    def test_exige_admin(self):
        self.client.logout()
        resp = self.client.get(self.url, {"png": "1"})
        self.assertEqual(resp.status_code, 302)


@override_settings(SITE_URL="https://achoupromos.com.br")
class QrCodeTests(Base):
    def test_acao_imprime_um_cartao_por_comercio(self):
        admin = get_user_model().objects.create_superuser("admin", password="senha-teste-123")
        self.client.force_login(admin)
        lojas = [self.comercio("Mercado Um"), self.comercio("Padaria Dois")]
        resp = self.client.post(
            reverse("admin:posts_comercio_changelist"),
            {"action": "imprimir_qrcodes", "_selected_action": [loja.pk for loja in lojas]},
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertEqual(html.count("<svg"), 2)
        self.assertIn("https://achoupromos.com.br/c/mercado-um/", html)
        self.assertIn("Padaria Dois", html)

    def test_qr_aponta_para_o_endereco(self):
        from .qr import qr_svg

        svg = qr_svg("https://achoupromos.com.br/c/mercado-um/?origem=qr")
        self.assertTrue(svg.startswith("<svg") or svg.startswith("<?xml"))
