"""
Configurações do Achou Promo.

No computador de desenvolvimento nada precisa ser configurado: os valores
padrão abaixo servem para rodar com `python manage.py runserver`.

No servidor, tudo que muda vem de variáveis de ambiente (arquivo
/srv/achoupromo/.env, veja deploy/env.exemplo):

    DJANGO_DEBUG=0
    DJANGO_SECRET_KEY=...           (obrigatório quando DEBUG=0)
    DJANGO_ALLOWED_HOSTS=achoupromos.com.br,www.achoupromos.com.br
    DJANGO_HTTPS=1                  (depois que o certificado estiver instalado)
    DJANGO_DB_PATH, DJANGO_MEDIA_ROOT, DJANGO_STATIC_ROOT
    SITE_URL=https://achoupromos.com.br
"""

import os
import re
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(nome, padrao=""):
    return os.environ.get(nome, padrao).strip()


def _env_bool(nome, padrao=False):
    return _env(nome, "1" if padrao else "0").lower() in ("1", "true", "sim", "yes", "on")


def _env_lista(nome, padrao=""):
    return [item.strip() for item in _env(nome, padrao).split(",") if item.strip()]


DEBUG = _env_bool("DJANGO_DEBUG", padrao=True)

SECRET_KEY = _env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY no servidor.")
    # Só para desenvolvimento. Nunca usada em produção.
    SECRET_KEY = "django-insecure-4%6)x!_+-q%@f@7)9#hbg!ts23#meow4kg1ug-!q+easw=46e9"

ALLOWED_HOSTS = _env_lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = _env_lista("DJANGO_CSRF_TRUSTED_ORIGINS")

# Endereço público do site (usado nos QR codes dos comércios).
SITE_URL = _env("SITE_URL", "https://achoupromos.com.br").rstrip("/")

# Perfil do Achou Promo no Instagram (sem @), mostrado no rodapé.
INSTAGRAM_SITE = _env("ACHOUPROMO_INSTAGRAM", "achoupromos3").lstrip("@")

# WhatsApp de quem vende os anúncios (com DDD). Se vazio, o botão "Anuncie" não aparece.
CONTATO_WHATSAPP = re.sub(r"\D", "", _env("ACHOUPROMO_CONTATO_WHATSAPP"))
if len(CONTATO_WHATSAPP) in (10, 11):
    CONTATO_WHATSAPP = "55" + CONTATO_WHATSAPP


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "posts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "posts.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _env("DJANGO_DB_PATH") or BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            # Espera em vez de dar erro se o admin e a vitrine escreverem ao mesmo tempo.
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# CSS/JS do site e do admin. No servidor o nginx serve a pasta STATIC_ROOT.
STATIC_URL = "static/"
if not DEBUG:
    # Nome do arquivo muda a cada versão (site.3fa1c2.css): o celular nunca fica com o visual antigo em cache.
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
    }
STATIC_ROOT = _env("DJANGO_STATIC_ROOT") or BASE_DIR / "staticfiles"

# Imagens enviadas no admin (promoções e logos). No servidor o nginx serve esta pasta.
MEDIA_URL = "media/"
MEDIA_ROOT = _env("DJANGO_MEDIA_ROOT") or BASE_DIR / "media"
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755


# HTTPS: ligado no servidor depois que o certificado (Let's Encrypt) estiver instalado.
if _env_bool("DJANGO_HTTPS"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(_env("DJANGO_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "descartar": {"class": "logging.NullHandler"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        # Robôs acessam o IP com endereços aleatórios; o Django recusa (400) e não precisa logar.
        "django.security.DisallowedHost": {"handlers": ["descartar"], "propagate": False},
    },
}


MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}

# O site não envia e-mail (não tem cadastro de consumidor nem "esqueci a senha").
# Se um dia enviar, configure um MAILERS de verdade e remova esta linha.
SILENCED_SYSTEM_CHECKS = [] if DEBUG else ["mail.E001"]
