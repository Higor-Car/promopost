import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Comercio, Promocao


def imagem_falsa():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    return SimpleUploadedFile("promo.png", buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT="/tmp/promopost_test_media")
class PromocaoTests(TestCase):
    def setUp(self):
        self.comercio = Comercio.objects.create(nome="Mercado Teste")
        usuario = get_user_model().objects.create_user("higor", password="senha-teste-123")
        self.client.force_login(usuario)

    def test_lista_abre(self):
        resp = self.client.get(reverse("lista_promocoes"))
        self.assertEqual(resp.status_code, 200)

    def test_cria_promocao(self):
        agora = timezone.now()
        resp = self.client.post(
            reverse("nova_promocao"),
            {
                "comercio": self.comercio.pk,
                "titulo": "Arroz em oferta",
                "legenda": "Só hoje!",
                "imagem": imagem_falsa(),
                "inicio": (agora + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
                "fim": (agora + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertRedirects(resp, reverse("lista_promocoes"))
        self.assertEqual(Promocao.objects.count(), 1)

    def test_fim_antes_do_inicio_e_invalido(self):
        agora = timezone.now()
        resp = self.client.post(
            reverse("nova_promocao"),
            {
                "comercio": self.comercio.pk,
                "titulo": "Errada",
                "imagem": imagem_falsa(),
                "inicio": (agora + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
                "fim": (agora + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Promocao.objects.count(), 0)
        self.assertContains(resp, "O fim da promoção precisa ser depois do início.", count=1)


@override_settings(MEDIA_ROOT="/tmp/promopost_test_media")
class AprovacaoTests(TestCase):
    def setUp(self):
        comercio = Comercio.objects.create(nome="Padaria Teste")
        agora = timezone.now()
        self.promocao = Promocao.objects.create(
            comercio=comercio,
            titulo="Pão a R$ 0,50",
            imagem=imagem_falsa(),
            inicio=agora + timedelta(hours=1),
            fim=agora + timedelta(days=1),
        )
        self.url = reverse("aprovar_promocao", args=[self.promocao.pk])
        self.usuario = get_user_model().objects.create_user("higor", password="senha-teste-123")

    def test_aprova_rascunho(self):
        self.client.force_login(self.usuario)
        resp = self.client.post(self.url)
        self.assertRedirects(resp, reverse("lista_promocoes"))
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.APROVADA)

    def test_get_nao_aprova(self):
        self.client.force_login(self.usuario)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.RASCUNHO)

    def test_nao_reaprova_promocao_publicada(self):
        self.promocao.status = Promocao.Status.PUBLICADA
        self.promocao.save()
        self.client.force_login(self.usuario)
        self.client.post(self.url)
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.PUBLICADA)

    def test_exige_login(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.RASCUNHO)


def _minuto(dt):
    return dt.replace(second=0, microsecond=0)


@override_settings(MEDIA_ROOT="/tmp/promopost_test_media")
class EdicaoExclusaoTests(TestCase):
    def setUp(self):
        self.comercio = Comercio.objects.create(nome="Açougue Teste")
        agora = timezone.now()
        self.inicio = _minuto(agora + timedelta(hours=1))
        self.fim = _minuto(agora + timedelta(days=1))
        self.promocao = Promocao.objects.create(
            comercio=self.comercio,
            titulo="Picanha em oferta",
            imagem=imagem_falsa(),
            inicio=self.inicio,
            fim=self.fim,
        )
        self.editar = reverse("editar_promocao", args=[self.promocao.pk])
        self.excluir = reverse("excluir_promocao", args=[self.promocao.pk])
        usuario = get_user_model().objects.create_user("higor", password="senha-teste-123")
        self.client.force_login(usuario)

    def dados(self, **extra):
        local = timezone.localtime
        dados = {
            "comercio": self.comercio.pk,
            "titulo": self.promocao.titulo,
            "legenda": self.promocao.legenda,
            "inicio": local(self.inicio).strftime("%Y-%m-%dT%H:%M"),
            "fim": local(self.fim).strftime("%Y-%m-%dT%H:%M"),
        }
        dados.update(extra)
        return dados

    def mudar_status(self, status):
        self.promocao.status = status
        self.promocao.save()

    # --- editar ---

    def test_formulario_de_edicao_abre(self):
        resp = self.client.get(self.editar)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Picanha em oferta")

    def test_edita_titulo_sem_reenviar_imagem(self):
        imagem = self.promocao.imagem.name
        resp = self.client.post(self.editar, self.dados(titulo="Picanha R$ 49,90"))
        self.assertRedirects(resp, reverse("lista_promocoes"))
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.titulo, "Picanha R$ 49,90")
        self.assertEqual(self.promocao.imagem.name, imagem)

    def test_edicao_valida_datas(self):
        resp = self.client.post(
            self.editar,
            self.dados(inicio=timezone.localtime(self.fim).strftime("%Y-%m-%dT%H:%M"),
                       fim=timezone.localtime(self.inicio).strftime("%Y-%m-%dT%H:%M")),
        )
        self.assertEqual(resp.status_code, 200)
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.inicio, self.inicio)

    def test_trocar_imagem_apaga_a_antiga(self):
        antiga = self.promocao.imagem
        storage, nome_antigo = antiga.storage, antiga.name
        self.client.post(self.editar, self.dados(imagem=imagem_falsa()))
        self.promocao.refresh_from_db()
        self.assertNotEqual(self.promocao.imagem.name, nome_antigo)
        self.assertFalse(storage.exists(nome_antigo))
        self.assertTrue(storage.exists(self.promocao.imagem.name))

    def test_editar_aprovada_volta_para_rascunho(self):
        self.mudar_status(Promocao.Status.APROVADA)
        self.client.post(self.editar, self.dados(titulo="Outro título"))
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.RASCUNHO)

    def test_salvar_aprovada_sem_mudancas_mantem_status(self):
        self.mudar_status(Promocao.Status.APROVADA)
        self.client.post(self.editar, self.dados())
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.APROVADA)

    def test_nao_edita_agendada(self):
        self.mudar_status(Promocao.Status.AGENDADA)
        resp = self.client.post(self.editar, self.dados(titulo="Hackeado"))
        self.assertRedirects(resp, reverse("lista_promocoes"))
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.titulo, "Picanha em oferta")

    # --- excluir ---

    def test_get_mostra_confirmacao_sem_excluir(self):
        resp = self.client.get(self.excluir)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tem certeza?")
        self.assertTrue(Promocao.objects.filter(pk=self.promocao.pk).exists())

    def test_post_exclui_promocao_e_imagem(self):
        storage, nome = self.promocao.imagem.storage, self.promocao.imagem.name
        resp = self.client.post(self.excluir)
        self.assertRedirects(resp, reverse("lista_promocoes"))
        self.assertFalse(Promocao.objects.filter(pk=self.promocao.pk).exists())
        self.assertFalse(storage.exists(nome))

    def test_nao_exclui_publicada(self):
        self.mudar_status(Promocao.Status.PUBLICADA)
        self.client.post(self.excluir)
        self.assertTrue(Promocao.objects.filter(pk=self.promocao.pk).exists())

    def test_editar_e_excluir_exigem_login(self):
        self.client.logout()
        for url in (self.editar, self.excluir):
            resp = self.client.post(url, self.dados(titulo="X"))
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse("login"), resp.url)
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.titulo, "Picanha em oferta")

    def test_lista_mostra_botoes_conforme_status(self):
        resp = self.client.get(reverse("lista_promocoes"))
        self.assertContains(resp, self.editar)
        self.assertContains(resp, self.excluir)
        self.mudar_status(Promocao.Status.PUBLICADA)
        resp = self.client.get(reverse("lista_promocoes"))
        self.assertNotContains(resp, self.editar)
        self.assertNotContains(resp, self.excluir)


class LoginTests(TestCase):
    def test_lista_exige_login(self):
        resp = self.client.get(reverse("lista_promocoes"))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('lista_promocoes')}")

    def test_nova_promocao_exige_login(self):
        resp = self.client.get(reverse("nova_promocao"))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('nova_promocao')}")

    def test_login_com_senha_correta(self):
        get_user_model().objects.create_user("higor", password="senha-teste-123")
        resp = self.client.post(reverse("login"), {"username": "higor", "password": "senha-teste-123"})
        self.assertRedirects(resp, reverse("lista_promocoes"))
