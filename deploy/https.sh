#!/usr/bin/env bash
# Instala o certificado HTTPS (Let's Encrypt, grátis e renovado sozinho).
# Só funciona DEPOIS que achoupromo.com.br e www.achoupromo.com.br apontarem para o IP do servidor.
# Uso: sudo bash /srv/achoupromo/app/deploy/https.sh seu-email@exemplo.com
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then echo "Rode com sudo."; exit 1; fi
if [ $# -lt 1 ]; then echo "Uso: sudo bash https.sh SEU_EMAIL (para avisos de vencimento)"; exit 1; fi

certbot --nginx --non-interactive --agree-tos --redirect -m "$1" \
    -d achoupromo.com.br -d www.achoupromo.com.br

sed -i 's/^DJANGO_HTTPS=.*/DJANGO_HTTPS=1/' /srv/achoupromo/.env
systemctl restart achoupromo
echo "HTTPS ligado: https://achoupromo.com.br"
