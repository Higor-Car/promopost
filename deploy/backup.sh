#!/usr/bin/env bash
# Cópia do banco (segura mesmo com o site no ar). Roda todo dia às 03:30 pelo cron.
# As fotos ficam em /srv/achoupromo/media; para elas, use os snapshots do Lightsail.
set -euo pipefail

DESTINO=/srv/achoupromo/backups
ARQUIVO=$DESTINO/db-$(date +%Y-%m-%d_%H%M).sqlite3

sqlite3 /srv/achoupromo/dados/db.sqlite3 ".backup '$ARQUIVO'"
gzip -f "$ARQUIVO"
chown achoupromo:www-data "$ARQUIVO.gz"
find "$DESTINO" -name 'db-*.sqlite3.gz' -mtime +14 -delete
echo "Backup: $ARQUIVO.gz"
