#!/usr/bin/env bash
# Troca o domínio do site no servidor (.env + nginx). O IP continua funcionando.
# Uso: sudo bash /srv/achoupromo/app/deploy/trocar-dominio.sh achoupromos.com.br
#
# Se o HTTPS já estava ligado no domínio antigo, ele é desligado aqui;
# depois que o domínio novo apontar para o servidor, rode o https.sh de novo.
set -euo pipefail

BASE=/srv/achoupromo
ENV=$BASE/.env
SITE=/etc/nginx/sites-available/achoupromo

if [ "$(id -u)" -ne 0 ]; then echo "Rode com sudo."; exit 1; fi
if [ $# -ne 1 ]; then echo "Uso: sudo bash trocar-dominio.sh NOVO_DOMINIO (sem www, sem https)"; exit 1; fi

NOVO=$(echo "$1" | tr 'A-Z' 'a-z' | sed -e 's|^https\?://||' -e 's|^www\.||' -e 's|/.*||')
if ! echo "$NOVO" | grep -Eq '^[a-z0-9-]+(\.[a-z0-9-]+)+$'; then echo "Domínio inválido: $1"; exit 1; fi

ANTIGO=$(sed -n 's|^SITE_URL=https\?://||p' $ENV | cut -d/ -f1)
# IPs que já estavam liberados continuam (ex.: acesso direto pelo IP fixo).
IPS=$(sed -n 's|^DJANGO_ALLOWED_HOSTS=||p' $ENV | tr ',' '\n' | { grep -E '^[0-9.]+$|:' || true; } | paste -sd, -)
HOSTS="$NOVO,www.$NOVO${IPS:+,$IPS}"

cp -a $ENV "$ENV.antes-de-$NOVO"
sed -i \
    -e "s|^DJANGO_ALLOWED_HOSTS=.*|DJANGO_ALLOWED_HOSTS=$HOSTS|" \
    -e "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*|DJANGO_CSRF_TRUSTED_ORIGINS=https://$NOVO,https://www.$NOVO|" \
    -e "s|^SITE_URL=.*|SITE_URL=https://$NOVO|" \
    -e "s|^DJANGO_HTTPS=.*|DJANGO_HTTPS=0|" \
    $ENV
echo ">> .env: $ANTIGO -> $NOVO (cópia do anterior em $ENV.antes-de-$NOVO)"

# A configuração do nginx com certificado do domínio antigo não serve mais: volta para a básica.
if [ -f $SITE ] && grep -q "managed by Certbot" $SITE; then
    cp -a $SITE "$SITE.antes-de-$NOVO"
    rm -f $SITE
    echo ">> HTTPS do domínio antigo desligado (rode o https.sh para o novo quando o DNS estiver pronto)."
fi

# Reaplica nginx e reinicia o site com o domínio novo.
exec bash $BASE/app/deploy/instalar.sh
