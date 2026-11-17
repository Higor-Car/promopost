import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Comercio, Postagem, Promocao


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

    def test_aprova_rascunho_e_agenda_postagens(self):
        self.client.force_login(self.usuario)
        resp = self.client.post(self.url)
        self.assertRedirects(resp, reverse("lista_promocoes"))
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.AGENDADA)
        postagens = self.promocao.postagens.all()
        self.assertEqual(sorted(p.rede for p in postagens), ["facebook", "instagram"])
        for postagem in postagens:
            self.assertEqual(postagem.agendada_para, self.promocao.inicio)
            self.assertEqual(postagem.status, Postagem.Status.PENDENTE)

    def test_inicio_no_passado_agenda_para_agora(self):
        self.promocao.inicio = timezone.now() - timedelta(hours=3)
        self.promocao.save()
        self.client.force_login(self.usuario)
        antes = timezone.now()
        self.client.post(self.url)
        for postagem in self.promocao.postagens.all():
            self.assertGreaterEqual(postagem.agendada_para, antes)

    def test_nao_aprova_promocao_que_ja_terminou(self):
        self.promocao.inicio = timezone.now() - timedelta(days=3)
        self.promocao.fim = timezone.now() - timedelta(days=1)
        self.promocao.save()
        self.client.force_login(self.usuario)
        self.client.post(self.url)
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.RASCUNHO)
        self.assertFalse(self.promocao.postagens.exists())

    def test_agendar_duas_vezes_nao_duplica(self):
        from .agendamento import agendar_promocao

        agendar_promocao(self.promocao)
        agendar_promocao(self.promocao)
        self.assertEqual(self.promocao.postagens.count(), 2)

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

    def test_editar_agendada_cancela_agendamento(self):
        from .agendamento import agendar_promocao

        agendar_promocao(self.promocao)
        self.client.post(self.editar, self.dados(titulo="Picanha R$ 49,90"))
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.RASCUNHO)
        self.assertFalse(self.promocao.postagens.exists())

    def test_nao_edita_nem_exclui_com_postagem_publicada(self):
        from .agendamento import agendar_promocao

        agendar_promocao(self.promocao)
        self.promocao.postagens.filter(rede="instagram").update(status=Postagem.Status.PUBLICADA)
        resp = self.client.post(self.editar, self.dados(titulo="Hackeado"))
        self.assertRedirects(resp, reverse("lista_promocoes"))
        self.client.post(self.excluir)
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.titulo, "Picanha em oferta")

    def test_nao_edita_encerrada(self):
        self.mudar_status(Promocao.Status.ENCERRADA)
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


@override_settings(MEDIA_ROOT="/tmp/promopost_test_media")
class AgendadorTests(TestCase):
    def setUp(self):
        from .agendamento import agendar_promocao

        self.agora = timezone.now()
        comercio = Comercio.objects.create(nome="Farmácia Teste")
        self.promocao = Promocao.objects.create(
            comercio=comercio,
            titulo="Vitamina C",
            imagem=imagem_falsa(),
            inicio=self.agora + timedelta(hours=1),
            fim=self.agora + timedelta(days=1),
        )
        agendar_promocao(self.promocao, self.agora)
        self.instagram = self.promocao.postagens.get(rede="instagram")
        self.facebook = self.promocao.postagens.get(rede="facebook")
        self.usuario = get_user_model().objects.create_user("higor", password="senha-teste-123")

    def processar(self, quando):
        from .agendamento import processar

        resultado = processar(quando)
        self.promocao.refresh_from_db()
        return resultado

    def test_antes_do_horario_nada_na_hora(self):
        resultado = self.processar(self.agora + timedelta(minutes=30))
        self.assertEqual(resultado["na_hora"], 0)
        self.assertEqual(self.promocao.status, Promocao.Status.AGENDADA)

    def test_no_horario_postagens_ficam_na_hora(self):
        resultado = self.processar(self.agora + timedelta(hours=2))
        self.assertEqual(resultado["na_hora"], 2)

    def test_encerra_no_fim_e_marca_erro_no_que_nao_saiu(self):
        resultado = self.processar(self.agora + timedelta(days=2))
        self.assertEqual(resultado["encerradas"], 1)
        self.assertEqual(self.promocao.status, Promocao.Status.ENCERRADA)
        for postagem in self.promocao.postagens.all():
            self.assertEqual(postagem.status, Postagem.Status.ERRO)
            self.assertIn("terminou", postagem.erro)

    def test_encerra_rascunho_vencido(self):
        rascunho = Promocao.objects.create(
            comercio=self.promocao.comercio,
            titulo="Esquecida",
            imagem=imagem_falsa(),
            inicio=self.agora - timedelta(days=3),
            fim=self.agora - timedelta(days=1),
        )
        self.processar(self.agora)
        rascunho.refresh_from_db()
        self.assertEqual(rascunho.status, Promocao.Status.ENCERRADA)

    def test_agenda_aprovada_pelo_admin(self):
        aprovada = Promocao.objects.create(
            comercio=self.promocao.comercio,
            titulo="Aprovada no admin",
            imagem=imagem_falsa(),
            inicio=self.agora + timedelta(hours=1),
            fim=self.agora + timedelta(days=1),
            status=Promocao.Status.APROVADA,
        )
        resultado = self.processar(self.agora)
        aprovada.refresh_from_db()
        self.assertEqual(resultado["agendadas"], 1)
        self.assertEqual(aprovada.status, Promocao.Status.AGENDADA)
        self.assertEqual(aprovada.postagens.count(), 2)

    def test_marcar_as_duas_redes_publica_a_promocao(self):
        self.client.force_login(self.usuario)
        self.client.post(reverse("marcar_publicada", args=[self.instagram.pk]))
        self.promocao.refresh_from_db()
        self.instagram.refresh_from_db()
        self.assertEqual(self.instagram.status, Postagem.Status.PUBLICADA)
        self.assertIsNotNone(self.instagram.publicada_em)
        self.assertEqual(self.promocao.status, Promocao.Status.AGENDADA)  # falta o Facebook

        self.client.post(reverse("marcar_publicada", args=[self.facebook.pk]))
        self.promocao.refresh_from_db()
        self.assertEqual(self.promocao.status, Promocao.Status.PUBLICADA)

    def test_nao_marca_publicada_em_promocao_encerrada(self):
        self.processar(self.agora + timedelta(days=2))
        self.client.force_login(self.usuario)
        self.client.post(reverse("marcar_publicada", args=[self.instagram.pk]))
        self.instagram.refresh_from_db()
        self.assertEqual(self.instagram.status, Postagem.Status.ERRO)

    def test_marcar_publicada_exige_login_e_post(self):
        url = reverse("marcar_publicada", args=[self.instagram.pk])
        resp = self.client.post(url)
        self.assertIn(reverse("login"), resp.url)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.instagram.refresh_from_db()
        self.assertEqual(self.instagram.status, Postagem.Status.PENDENTE)

    def test_next_externo_e_ignorado(self):
        self.client.force_login(self.usuario)
        resp = self.client.post(
            reverse("marcar_publicada", args=[self.instagram.pk]), {"next": "https://site-malicioso.com/"}
        )
        self.assertRedirects(resp, reverse("lista_promocoes"))

    def test_comando_roda(self):
        from django.core.management import call_command

        saida = io.StringIO()
        call_command("processar_agendamentos", stdout=saida)
        self.assertIn("na hora de postar", saida.getvalue())


@override_settings(MEDIA_ROOT="/tmp/promopost_test_media")
class CalendarioTests(TestCase):
    def setUp(self):
        from .agendamento import agendar_promocao

        comercio = Comercio.objects.create(nome="Loja Teste", instagram="@lojateste")
        agora = timezone.now()
        self.passada = Promocao.objects.create(
            comercio=comercio, titulo="Já começou", legenda="Corre que acaba!", imagem=imagem_falsa(),
            inicio=agora - timedelta(hours=1), fim=agora + timedelta(days=1),
        )
        self.futura = Promocao.objects.create(
            comercio=comercio, titulo="Mês que vem", imagem=imagem_falsa(),
            inicio=agora + timedelta(days=40), fim=agora + timedelta(days=45),
        )
        agendar_promocao(self.passada)
        agendar_promocao(self.futura)
        self.usuario = get_user_model().objects.create_user("higor", password="senha-teste-123")
        self.client.force_login(self.usuario)
        self.url = reverse("calendario")

    def test_mostra_hora_de_postar_com_legenda_e_botao(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "Hora de postar (2)")
        self.assertContains(resp, "Corre que acaba!")
        self.assertContains(resp, "@lojateste")
        for postagem in self.passada.postagens.all():
            self.assertContains(resp, reverse("marcar_publicada", args=[postagem.pk]))

    def test_mes_atual_nao_mostra_postagem_do_mes_seguinte(self):
        resp = self.client.get(self.url)
        self.assertNotContains(resp, "Mês que vem")

    def test_navega_para_o_mes_da_postagem(self):
        mes = timezone.localtime(self.futura.inicio).strftime("%Y-%m")
        resp = self.client.get(self.url, {"mes": mes})
        self.assertContains(resp, "Mês que vem")

    def test_mes_invalido_usa_mes_atual(self):
        for mes in ("abc", "2026-13", "2026"):
            resp = self.client.get(self.url, {"mes": mes})
            self.assertEqual(resp.status_code, 200)

    def test_virada_de_ano(self):
        resp = self.client.get(self.url, {"mes": "2026-12"})
        self.assertContains(resp, "?mes=2027-01")
        self.assertContains(resp, "?mes=2026-11")

    def test_marcar_publicada_volta_para_o_calendario(self):
        postagem = self.passada.postagens.first()
        resp = self.client.post(
            reverse("marcar_publicada", args=[postagem.pk]), {"next": self.url}
        )
        self.assertRedirects(resp, self.url)
        resp = self.client.get(self.url)
        self.assertContains(resp, "Hora de postar (1)")

    def test_exige_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertIn(reverse("login"), resp.url)
