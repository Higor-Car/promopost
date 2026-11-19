import re
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Cidade(models.TextChoices):
    MAURILANDIA = "maurilandia", "Maurilândia"
    TURVELANDIA = "turvelandia", "Turvelândia"


class Categoria(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True, help_text="Usado no endereço do filtro.")
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
    whatsapp = models.CharField(
        max_length=20, blank=True, help_text="Com DDD. Ex.: (64) 99999-1234"
    )
    instagram = models.CharField("Instagram (@)", max_length=60, blank=True)
    plano = models.CharField(max_length=10, choices=Plano.choices, default=Plano.BASICO)
    mensalidade = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True, help_text="Desmarque para tirar o comércio da vitrine.")
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

    def link_whatsapp(self, mensagem=""):
        if not self.whatsapp_numero:
            return ""
        link = f"https://wa.me/{self.whatsapp_numero}"
        if mensagem:
            link += "?text=" + quote(mensagem)
        return link

    @property
    def instagram_usuario(self):
        return self.instagram.strip().lstrip("@").split("/")[-1] if self.instagram.strip() else ""


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
    imagem = models.ImageField(upload_to="promocoes/%Y/%m/")
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

    def link_whatsapp(self):
        return self.comercio.link_whatsapp(
            f"Olá! Vi a promoção \"{self.titulo}\" no Achou Promo e quero saber mais."
        )
