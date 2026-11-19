#!/usr/bin/env bash
# Roda um comando do Django no servidor com as configurações de produção.
# Ex.: sudo bash /srv/achoupromo/app/deploy/manage.sh createsuperuser
set -euo pipefail
BASE=/srv/achoupromo
cd $BASE/app
exec sudo -u achoupromo bash -c "set -a; source $BASE/.env; set +a; $BASE/venv/bin/python manage.py $(printf '%q ' "$@")"
