#!/usr/bin/env bash
# Instala o certificado HTTPS (Let's Encrypt, grátis e renovado sozinho) para o domínio do .env.
# Só funciona DEPOIS que o domínio e o www apontarem para o IP do servidor.
# Uso: sudo bash /srv/achoupromo/app/deploy/https.sh seu-email@exemplo.com
set -euo pipefail

ENV=/srv/achoupromo/.env

if [ "$(id -u)" -ne 0 ]; then echo "Rode com sudo."; exit 1; fi
if [ $# -lt 1 ]; then echo "Uso: sudo bash https.sh SEU_EMAIL (para avisos de vencimento)"; exit 1; fi

DOMINIO=$(sed -n 's|^SITE_URL=https\?://||p' $ENV | cut -d/ -f1)
echo ">> Certificado para $DOMINIO e www.$DOMINIO"

certbot --nginx --non-interactive --agree-tos --redirect -m "$1" \
    -d "$DOMINIO" -d "www.$DOMINIO"

sed -i 's/^DJANGO_HTTPS=.*/DJANGO_HTTPS=1/' $ENV
systemctl restart achoupromo
echo "HTTPS ligado: https://$DOMINIO"
