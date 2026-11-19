import re
import secrets
import unicodedata
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Cidade(models.TextChoices):
    MAURILANDIA = "maurilandia", "Maurilândia"
    TURVELANDIA = "turvelandia", "Turvelândia"
    PORTEIRAO = "porteirao", "Porteirão"


def normalizar(texto):
    """Minúsculas e sem acento, para a busca achar "acougue" em "Açougue"."""
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def novo_token():
    return secrets.token_urlsafe(16)


class Categoria(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True, help_text="Usado no endereço do filtro.")
    icone = models.CharField("ícone", max_length=8, blank=True, help_text="Um emoji. Ex.: 🛒")
    ordem = models.PositiveSmallIntegerField(default=0, help_text="Menor aparece primeiro.")

    class Meta:
        ordering = ["ordem", "nome"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class Comercio(models.Model):
    class Plano(models.TextChoices):
        BASICO = "basico", "Básico (promoção mensal)"
        SEMANAL = "semanal", "Semanal"
        DIARIO = "diario", "Diário"

    nome = models.CharField(max_length=120)
    slug = models.SlugField(
        max_length=140, unique=True, help_text="Endereço da página do comércio no site: /c/<slug>/"
    )
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="comercios")
    cidade = models.CharField(max_length=20, choices=Cidade.choices, default=Cidade.MAURILANDIA)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    descricao = models.TextField("descrição", blank=True)
    logo = models.ImageField(upload_to="comercios/", blank=True)
    capa = models.ImageField(
        "foto de capa", upload_to="comercios/capas/", blank=True,
        help_text="Opcional. Foto horizontal da fachada ou dos produtos; aparece no topo da página da loja.",
    )
    horario = models.TextField(
        "horário de funcionamento", blank=True,
        help_text="Uma linha por dia ou faixa. Ex.: Seg a sex: 7h às 19h / Sáb: 7h às 13h",
    )
    whatsapp = models.CharField(
        max_length=20, blank=True, help_text="Com DDD. Ex.: (64) 99999-1234"
    )
    mostrar_whatsapp = models.BooleanField(
        "mostrar botão de WhatsApp no site", default=True,
        help_text="Desmarque se a loja quer aparecer só com as promoções, sem botão nem número de WhatsApp.",
    )
    instagram = models.CharField("Instagram (@)", max_length=60, blank=True)
    plano = models.CharField(max_length=10, choices=Plano.choices, default=Plano.BASICO)
    mensalidade = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True, help_text="Desmarque para tirar o comércio da vitrine.")
    token_resultado = models.CharField(
        "código do link de resultado", max_length=32, unique=True, default=novo_token, editable=False,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "comércio"
        verbose_name_plural = "comércios"

    def __str__(self):
        return f"{self.nome} ({self.get_cidade_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)[:140]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("comercio", args=[self.slug])

    @property
    def whatsapp_numero(self):
        """Só dígitos, com código do Brasil (55) na frente."""
        digitos = re.sub(r"\D", "", self.whatsapp)
        if not digitos:
            return ""
        if len(digitos) in (10, 11):  # DDD + número
            digitos = "55" + digitos
        return digitos

    @property
    def whatsapp_visivel(self):
        return bool(self.mostrar_whatsapp and self.whatsapp_numero)

    def link_whatsapp(self, mensagem=""):
        if not self.whatsapp_visivel:
            return ""
        link = f"https://wa.me/{self.whatsapp_numero}"
        if mensagem:
            link += "?text=" + quote(mensagem)
        return link

    @property
    def instagram_usuario(self):
        return self.instagram.strip().rstrip("/").lstrip("@").split("/")[-1] if self.instagram.strip() else ""

    @property
    def link_mapa(self):
        if not self.endereco:
            return ""
        busca = f"{self.endereco}, {self.get_cidade_display()} - GO"
        return "https://www.google.com/maps/search/?api=1&query=" + quote(busca)

    def get_resultado_url(self):
        return reverse("resultado", args=[self.token_resultado])

    CORES_CAPA = ("#ea580c", "#0f766e", "#7c3aed", "#be123c", "#1d4ed8", "#b45309", "#15803d", "#c026d3")

    @property
    def cor_capa(self):
        """Cor da capa desenhada quando a loja não tem foto de capa (fixa por loja)."""
        return self.CORES_CAPA[(self.pk or 0) % len(self.CORES_CAPA)]

    @property
    def whatsapp_formatado(self):
        d = self.whatsapp_numero[2:] if self.whatsapp_numero.startswith("55") else self.whatsapp_numero
        if len(d) == 11:
            return f"({d[:2]}) {d[2:7]}-{d[7:]}"
        if len(d) == 10:
            return f"({d[:2]}) {d[2:6]}-{d[6:]}"
        return self.whatsapp


class PromocaoQuerySet(models.QuerySet):
    def ativas(self, agora=None):
        """Promoções que estão valendo agora, de comércios ativos."""
        agora = agora or timezone.now()
        return self.filter(inicio__lte=agora, fim__gt=agora, comercio__ativo=True)


class Promocao(models.Model):
    comercio = models.ForeignKey(
        Comercio, on_delete=models.CASCADE, related_name="promocoes", verbose_name="comércio"
    )
    titulo = models.CharField("título", max_length=150)
    descricao = models.TextField("descrição", blank=True)
    imagem = models.ImageField(
        upload_to="promocoes/%Y/%m/",
        help_text="Qualquer formato: quadrada, retrato ou story. A arte aparece inteira no site, sem cortes.",
    )
    preco = models.DecimalField(
        "preço", max_digits=9, decimal_places=2, null=True, blank=True,
        help_text="Opcional. Preço da promoção.",
    )
    preco_de = models.DecimalField(
        "preço antes", max_digits=9, decimal_places=2, null=True, blank=True,
        help_text="Opcional. Aparece riscado (\"de R$ X por R$ Y\").",
    )
    inicio = models.DateTimeField("aparece a partir de", default=timezone.now)
    fim = models.DateTimeField("válida até", help_text="Depois desse horário some da vitrine.")
    destaque = models.BooleanField(default=False, help_text="Aparece primeiro, com selo de destaque.")
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = PromocaoQuerySet.as_manager()

    class Meta:
        ordering = ["-destaque", "fim"]
        verbose_name = "promoção"
        verbose_name_plural = "promoções"

    def __str__(self):
        return f"{self.titulo} - {self.comercio.nome}"

    def get_absolute_url(self):
        return reverse("promocao", args=[self.pk])

    def clean(self):
        erros = {}
        if self.inicio and self.fim and self.fim <= self.inicio:
            erros["fim"] = "A validade precisa ser depois do início."
        if self.preco is not None and self.preco_de is not None and self.preco_de <= self.preco:
            erros["preco_de"] = "O preço antes precisa ser maior que o preço da promoção."
        if erros:
            raise ValidationError(erros)

    @property
    def ativa(self):
        agora = timezone.now()
        return self.inicio <= agora < self.fim and self.comercio.ativo

    @property
    def acaba_hoje(self):
        return timezone.localdate(self.fim) == timezone.localdate()

    @property
    def desconto(self):
        """Porcentagem de desconto (ex.: 17) quando há preço e preço antes."""
        if self.preco is None or not self.preco_de or self.preco_de <= self.preco:
            return None
        return round((1 - self.preco / self.preco_de) * 100)

    def texto_busca(self):
        partes = [self.titulo, self.descricao, self.comercio.nome, self.comercio.categoria.nome]
        return normalizar(" ".join(partes))

    def link_whatsapp(self):
        return self.comercio.link_whatsapp(
            f"Olá! Vi a promoção \"{self.titulo}\" no Achou Promo e quero saber mais."
        )


class MetricaDiaria(models.Model):
    """Contadores por dia, comércio, promoção e tipo de acesso. Não guarda IP nem dados pessoais."""

    class Tipo(models.TextChoices):
        IMPRESSAO = "impressao", "Apareceu na vitrine"
        VISITA_PROMOCAO = "visita_promocao", "Abriu a promoção"
        VISITA_COMERCIO = "visita_comercio", "Visitou a página da loja"
        WHATSAPP = "whatsapp", "Clicou no WhatsApp"
        INSTAGRAM = "instagram", "Clicou no Instagram"
        MAPA = "mapa", "Clicou em Como chegar"
        QR = "qr", "Chegou pelo QR code"

    dia = models.DateField()
    chave = models.CharField(max_length=60, editable=False)
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name="metricas")
    promocao = models.ForeignKey(
        Promocao, on_delete=models.SET_NULL, null=True, blank=True, related_name="metricas"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    total = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "métrica diária"
        verbose_name_plural = "métricas diárias"
        constraints = [models.UniqueConstraint(fields=["dia", "chave"], name="metrica_unica_por_dia")]
        indexes = [models.Index(fields=["comercio", "dia"])]

    def __str__(self):
        return f"{self.dia} {self.comercio_id} {self.tipo}: {self.total}"
