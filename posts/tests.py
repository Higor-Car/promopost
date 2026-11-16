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
