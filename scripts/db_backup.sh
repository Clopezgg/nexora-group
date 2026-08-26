#!/usr/bin/env bash
set -euo pipefail

# NXR-REQ-0109 (Backup/Restore). Backup real vía pg_dump, formato custom
# (--format=custom): comprimido y restaurable con pg_restore de forma
# selectiva si algún día hace falta. --no-owner/--no-privileges para que
# el dump sea portable entre roles distintos (dev local vs Azure
# Postgres Flexible Server más adelante).
DB_NAME="${1:?uso: db_backup.sh <db_name> <archivo_salida.dump>}"
OUTPUT="${2:?uso: db_backup.sh <db_name> <archivo_salida.dump>}"

pg_dump --format=custom --no-owner --no-privileges --dbname="$DB_NAME" --file="$OUTPUT"
echo "Backup real de '$DB_NAME' escrito en $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
