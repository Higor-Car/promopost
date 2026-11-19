#!/usr/bin/env bash
# Publica a versão mais nova do GitHub no servidor.
# Uso: sudo bash /srv/achoupromo/app/deploy/atualizar.sh
set -euo pipefail

BASE=/srv/achoupromo
APP=$BASE/app

if [ "$(id -u)" -ne 0 ]; then echo "Rode com sudo."; exit 1; fi

echo ">> Backup do banco antes de atualizar"
/usr/local/bin/achoupromo-backup

echo ">> Baixando código novo"
chown -R achoupromo: $APP
sudo -u achoupromo git -C $APP pull --ff-only

# Reaplica tudo (pacotes, permissões, migrações, nginx, serviço) com a versão nova do script.
exec bash $APP/deploy/instalar.sh
