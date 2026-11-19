#!/usr/bin/env bash
# Instala o Achou Promo num servidor Ubuntu 24.04 novo (ex.: AWS Lightsail).
# Rodar uma vez, como root:  sudo bash instalar.sh IP_OU_DOMINIO [IP_OU_DOMINIO ...]
# Pode rodar de novo sem estragar nada (não sobrescreve o .env nem o banco).
set -euo pipefail

REPO="https://github.com/Higor-Car/promopost.git"
BASE=/srv/achoupromo
APP=$BASE/app
VENV=$BASE/venv
USUARIO=achoupromo

if [ "$(id -u)" -ne 0 ]; then echo "Rode com sudo."; exit 1; fi
if [ $# -lt 1 ]; then echo "Uso: sudo bash instalar.sh IP_DO_SERVIDOR [dominios...]"; exit 1; fi
HOSTS="achoupromo.com.br,www.achoupromo.com.br,$(IFS=,; echo "$*")"

echo ">> Pacotes do sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3 python3-venv python3-dev build-essential git nginx sqlite3 \
    certbot python3-certbot-nginx unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades

echo ">> Usuário e pastas"
id -u $USUARIO >/dev/null 2>&1 || useradd --system --home $BASE --shell /usr/sbin/nologin --gid www-data $USUARIO
mkdir -p $BASE/dados $BASE/media $BASE/static $BASE/backups
chown $USUARIO:www-data $BASE $BASE/dados $BASE/media $BASE/static $BASE/backups
chmod 750 $BASE/dados $BASE/backups
chmod 755 $BASE $BASE/media $BASE/static

echo ">> Código"
if [ -d $APP/.git ]; then
    sudo -u $USUARIO git -C $APP pull --ff-only
else
    sudo -u $USUARIO git clone $REPO $APP
fi

echo ">> Python"
[ -d $VENV ] || sudo -u $USUARIO python3 -m venv $VENV
sudo -u $USUARIO $VENV/bin/pip install -q --upgrade pip
sudo -u $USUARIO $VENV/bin/pip install -q -r $APP/requirements.txt

echo ">> Configuração (.env)"
if [ ! -f $BASE/.env ]; then
    CHAVE=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$CHAVE|" \
        -e "s|^DJANGO_ALLOWED_HOSTS=.*|DJANGO_ALLOWED_HOSTS=$HOSTS|" \
        $APP/deploy/env.exemplo > $BASE/.env
    chown root:www-data $BASE/.env
    chmod 640 $BASE/.env
    echo "   .env criado com uma chave nova."
else
    echo "   .env já existe, mantido."
fi

echo ">> Banco e arquivos estáticos"
rodar() { sudo -u $USUARIO bash -c "set -a; source $BASE/.env; set +a; cd $APP; $VENV/bin/python manage.py $*"; }
rodar migrate --noinput
rodar collectstatic --noinput -v 0
rodar check --deploy --fail-level ERROR

echo ">> Serviços (gunicorn + nginx)"
cp $APP/deploy/achoupromo.service /etc/systemd/system/achoupromo.service
systemctl daemon-reload
systemctl enable --now achoupromo
systemctl restart achoupromo
if [ ! -f /etc/nginx/sites-available/achoupromo ] || ! grep -q "managed by Certbot" /etc/nginx/sites-available/achoupromo; then
    cp $APP/deploy/nginx.conf /etc/nginx/sites-available/achoupromo
fi
ln -sf /etc/nginx/sites-available/achoupromo /etc/nginx/sites-enabled/achoupromo
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ">> Backup diário do banco (03:30, guarda 14 dias)"
install -m 755 $APP/deploy/backup.sh /usr/local/bin/achoupromo-backup
echo "30 3 * * * root /usr/local/bin/achoupromo-backup" > /etc/cron.d/achoupromo-backup

echo
echo "Pronto! Crie o usuário do admin com:"
echo "  sudo bash $APP/deploy/manage.sh createsuperuser"
