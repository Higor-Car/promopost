from django.db import models


class Comercio(models.Model):
    class Plano(models.TextChoices):
        BASICO = "basico", "Básico (promoção mensal)"
        SEMANAL = "semanal", "Semanal"
        DIARIO = "diario", "Diário"

    nome = models.CharField(max_length=120)
    cidade = models.CharField(max_length=80, default="Maurilândia")
    whatsapp = models.CharField(max_length=20, blank=True)
    instagram = models.CharField("Instagram (@)", max_length=60, blank=True)
    plano = models.CharField(max_length=10, choices=Plano.choices, default=Plano.BASICO)
    mensalidade = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "comércio"
        verbose_name_plural = "comércios"

    def __str__(self):
        return f"{self.nome} ({self.cidade})"


class Promocao(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        AGUARDANDO = "aguardando", "Aguardando aprovação do cliente"
        APROVADA = "aprovada", "Aprovada"
        AGENDADA = "agendada", "Agendada"
        PUBLICADA = "publicada", "Publicada"
        ENCERRADA = "encerrada", "Encerrada"

    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name="promocoes")
    titulo = models.CharField(max_length=150)
    legenda = models.TextField(blank=True)
    imagem = models.ImageField(upload_to="promocoes/%Y/%m/")
    inicio = models.DateTimeField("início da publicação")
    fim = models.DateTimeField("fim da promoção")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["inicio"]
        verbose_name = "promoção"
        verbose_name_plural = "promoções"

    def __str__(self):
        return f"{self.titulo} - {self.comercio.nome}"


class Postagem(models.Model):
    """Uma publicação concreta de uma promoção em uma rede social."""

    class Rede(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PUBLICADA = "publicada", "Publicada"
        ERRO = "erro", "Erro"

    promocao = models.ForeignKey(Promocao, on_delete=models.CASCADE, related_name="postagens")
    rede = models.CharField(max_length=10, choices=Rede.choices)
    agendada_para = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    publicada_em = models.DateTimeField(null=True, blank=True)
    erro = models.TextField(blank=True)

    class Meta:
        ordering = ["agendada_para"]
        verbose_name_plural = "postagens"

    def __str__(self):
        return f"{self.get_rede_display()} - {self.promocao.titulo}"
