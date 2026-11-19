#!/usr/bin/env bash
# Publica a versão mais nova do GitHub no servidor.
# Uso: sudo bash /srv/achoupromo/app/deploy/atualizar.sh
set -euo pipefail

BASE=/srv/achoupromo
APP=$BASE/app
VENV=$BASE/venv
USUARIO=achoupromo

if [ "$(id -u)" -ne 0 ]; then echo "Rode com sudo."; exit 1; fi

echo ">> Backup do banco antes de atualizar"
/usr/local/bin/achoupromo-backup

echo ">> Baixando código novo"
sudo -u $USUARIO git -C $APP pull --ff-only
sudo -u $USUARIO $VENV/bin/pip install -q -r $APP/requirements.txt

echo ">> Banco e estáticos"
rodar() { sudo -u $USUARIO bash -c "set -a; source $BASE/.env; set +a; cd $APP; $VENV/bin/python manage.py $*"; }
rodar migrate --noinput
rodar collectstatic --noinput -v 0
rodar check --deploy --fail-level ERROR

echo ">> Reiniciando"
cp $APP/deploy/achoupromo.service /etc/systemd/system/achoupromo.service
systemctl daemon-reload
systemctl restart achoupromo
sleep 2
systemctl is-active --quiet achoupromo
echo "Atualizado: $(sudo -u $USUARIO git -C $APP log --oneline -1)"
