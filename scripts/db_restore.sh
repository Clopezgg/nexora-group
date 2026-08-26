#!/usr/bin/env bash
set -euo pipefail

# NXR-REQ-0109 (Backup/Restore). Restore real: recrea la DB destino desde
# cero (drop/create) y restaura el dump completo con pg_restore. Nunca
# restaura sobre una DB con datos existentes -- una restauración real de
# desastre siempre parte de un destino vacío y conocido.
DUMP="${1:?uso: db_restore.sh <archivo.dump> <db_destino>}"
TARGET="${2:?uso: db_restore.sh <archivo.dump> <db_destino>}"

dropdb --if-exists "$TARGET"
createdb "$TARGET"
pg_restore --no-owner --no-privileges --dbname="$TARGET" "$DUMP"
echo "Restore real completado en '$TARGET'"
