#!/usr/bin/env bash
# Instala (ou reconfigura) o Achou Promo num servidor Ubuntu 24.04 (ex.: AWS Lightsail).
#
# Primeira vez:   sudo bash instalar.sh IP_DO_SERVIDOR
# Outras vezes:   sudo bash instalar.sh          (o atualizar.sh já chama este script)
#
# Pode rodar quantas vezes quiser: não apaga o .env, o banco, as fotos nem o certificado.
set -euo pipefail

REPO="https://github.com/Higor-Car/promopost.git"
BASE=/srv/achoupromo
APP=$BASE/app
VENV=$BASE/venv
USUARIO=achoupromo

if [ "$(id -u)" -ne 0 ]; then echo "Rode com sudo."; exit 1; fi
if [ ! -f $BASE/.env ] && [ $# -lt 1 ]; then
    echo "Primeira instalação: sudo bash instalar.sh IP_DO_SERVIDOR"; exit 1
fi

echo ">> Pacotes do sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3 python3-venv python3-dev build-essential git nginx sqlite3 \
    certbot python3-certbot-nginx unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades

echo ">> Usuário e pastas"
# O site roda com um usuário próprio. O nginx (www-data) não consegue ler o banco nem o .env.
getent group $USUARIO >/dev/null || groupadd --system $USUARIO
if id -u $USUARIO >/dev/null 2>&1; then
    usermod -g $USUARIO $USUARIO   # versões antigas usavam o grupo www-data
else
    useradd --system --home $BASE --shell /usr/sbin/nologin --gid $USUARIO $USUARIO
fi
mkdir -p $BASE/dados $BASE/media $BASE/static $BASE/backups
chown $USUARIO:$USUARIO $BASE
chmod 755 $BASE

echo ">> Código"
if [ -d $APP/.git ]; then
    chown -R $USUARIO:$USUARIO $APP
    sudo -u $USUARIO git -C $APP pull --ff-only
else
    sudo -u $USUARIO git clone $REPO $APP
fi

echo ">> Python"
[ -d $VENV ] || sudo -u $USUARIO python3 -m venv $VENV
chown -R $USUARIO:$USUARIO $VENV
sudo -u $USUARIO $VENV/bin/pip install -q --upgrade pip
sudo -u $USUARIO $VENV/bin/pip install -q -r $APP/requirements.txt

echo ">> Configuração (.env)"
if [ ! -f $BASE/.env ]; then
    HOSTS="achoupromo.com.br,www.achoupromo.com.br,$(IFS=,; echo "$*")"
    CHAVE=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$CHAVE|" \
        -e "s|^DJANGO_ALLOWED_HOSTS=.*|DJANGO_ALLOWED_HOSTS=$HOSTS|" \
        $APP/deploy/env.exemplo > $BASE/.env
    echo "   .env criado com uma chave nova."
else
    echo "   .env já existe, mantido."
fi

echo ">> Permissões"
# .env: só root escreve, só o site lê.
chown root:$USUARIO $BASE/.env
chmod 640 $BASE/.env
# Banco e backups: só o site.
chown -R $USUARIO:$USUARIO $BASE/dados $BASE/backups
chmod 700 $BASE/dados $BASE/backups
find $BASE/dados $BASE/backups -type f -exec chmod 600 {} +
# Fotos e estáticos: públicos (o nginx precisa ler).
chown -R $USUARIO:$USUARIO $BASE/media $BASE/static
find $BASE/media $BASE/static -type d -exec chmod 755 {} +
find $BASE/media $BASE/static -type f -exec chmod 644 {} +

echo ">> Banco e arquivos estáticos"
rodar() { sudo -u $USUARIO bash -c "umask 027; set -a; source $BASE/.env; set +a; cd $APP; $VENV/bin/python manage.py $*"; }
rodar migrate --noinput
rodar collectstatic --noinput -v 0
find $BASE/static -type d -exec chmod 755 {} +
find $BASE/static -type f -exec chmod 644 {} +
rodar check --deploy --fail-level ERROR

echo ">> nginx (testa antes de trocar; se der erro, volta o anterior)"
SITE=/etc/nginx/sites-available/achoupromo
GERAL=/etc/nginx/conf.d/achoupromo.conf
LOCAIS=/etc/nginx/snippets/achoupromo-locais.conf
ANTERIOR=$(mktemp -d)
for f in $SITE $GERAL $LOCAIS /etc/nginx/sites-enabled/default; do
    [ -e "$f" ] && cp -a "$f" "$ANTERIOR/$(echo "$f" | tr / _)"
done
cp $APP/deploy/nginx-geral.conf $GERAL
cp $APP/deploy/nginx-locais.conf $LOCAIS
if [ ! -f $SITE ] || ! grep -q "managed by Certbot" $SITE; then
    cp $APP/deploy/nginx.conf $SITE
fi
ln -sf $SITE /etc/nginx/sites-enabled/achoupromo
rm -f /etc/nginx/sites-enabled/default
if ! nginx -t; then
    echo "!! Configuração nova do nginx com erro. Voltando a anterior; o site continua como estava."
    rm -f $GERAL $LOCAIS
    for f in $SITE $GERAL $LOCAIS /etc/nginx/sites-enabled/default; do
        b="$ANTERIOR/$(echo "$f" | tr / _)"
        [ -e "$b" ] && cp -a "$b" "$f"
    done
    nginx -t && systemctl reload nginx
    exit 1
fi

echo ">> Serviço do site (gunicorn) e nginx"
cp $APP/deploy/achoupromo.service /etc/systemd/system/achoupromo.service
systemctl daemon-reload
systemctl enable achoupromo
systemctl restart achoupromo
systemctl reload nginx

echo ">> Backup diário do banco (03:30, guarda 14 dias)"
install -m 755 $APP/deploy/backup.sh /usr/local/bin/achoupromo-backup
echo "30 3 * * * root /usr/local/bin/achoupromo-backup" > /etc/cron.d/achoupromo-backup

echo ">> Conferindo"
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s -o /dev/null -f -H "Host: localhost" http://127.0.0.1:8000/admin/login/; then break; fi
    sleep 2
done
systemctl is-active achoupromo
echo
echo "Pronto: $(sudo -u $USUARIO git -C $APP log --oneline -1)"
echo "Para criar um usuário do admin:  sudo bash $APP/deploy/manage.sh createsuperuser"
