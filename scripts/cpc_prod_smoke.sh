#!/usr/bin/env bash
# Smoke de producción — Control Contractual de Pagos (SOLO LECTURA, sin escribir
# nada en la base de datos de producción — §78).
#
# Uso:
#   ADMIN_EMAIL='...' ADMIN_PASSWORD='...' bash cpc_prod_smoke.sh
#
set -euo pipefail

FRONTEND_URL="https://jolly-plant-0d6bf700f.7.azurestaticapps.net"
API="$FRONTEND_URL/api"
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT

: "${ADMIN_EMAIL:?exporta ADMIN_EMAIL}"
: "${ADMIN_PASSWORD:?exporta ADMIN_PASSWORD}"

say() { printf '  %-52s %s\n' "$1" "$2"; }

echo "== Salud =="
say "readyz" "$(curl -s -o /dev/null -w '%{http_code}' "$API/readyz")"

echo "== Login first-party =="
code="$(curl -s -o /dev/null -w '%{http_code}' --cookie-jar "$JAR" \
  -H "Origin: $FRONTEND_URL" -H 'Content-Type: application/json' \
  -d "$(printf '{"email":"%s","password":"%s"}' "$ADMIN_EMAIL" "$ADMIN_PASSWORD")" \
  "$API/auth/login")"
say "auth/login" "$code"
[ "$code" = "200" ] || { echo "login falló"; exit 1; }

get() {
  curl -s --cookie "$JAR" -H "Origin: $FRONTEND_URL" \
    -o /tmp/cpc_smoke_body.json -w '%{http_code}' "$API$1"
}

CID="$(curl -s --cookie "$JAR" -H "Origin: $FRONTEND_URL" "$API/master-data/companies" | jq -r '.[0].id')"
echo "== Empresa activa: $CID =="

echo "== Endpoints CPC (solo lectura) =="
c=$(get "/contract-payments/schedules?companyId=$CID")
say "GET /contract-payments/schedules" "$c  ($(jq -r 'length' /tmp/cpc_smoke_body.json 2>/dev/null || echo '?') planes)"

c=$(get "/reports/contract-payment-ledger?companyId=$CID")
say "GET /reports/contract-payment-ledger" "$c  ($(jq -r '.entries|length' /tmp/cpc_smoke_body.json 2>/dev/null || echo '?') contratos)"

c=$(get "/reports/contract-payment-ledger?companyId=$CID&format=csv")
say "GET  ...contract-payment-ledger?format=csv" "$c"

c=$(get "/accounting/reconciliation/subledger-gl?companyId=$CID")
say "GET /accounting/reconciliation/subledger-gl" "$c"
jq -r '.lines[] | "       - \(.subledger): cuadra=\(.reconciled)"' /tmp/cpc_smoke_body.json 2>/dev/null || true

echo "== Verificación pública de comprobante (sin auth) =="
say "GET /verificar/comprobante/<inexistente>" "$(curl -s -o /dev/null -w '%{http_code}' "$API/verificar/comprobante/nope-not-a-real-token")"

curl -s --cookie "$JAR" -H "Origin: $FRONTEND_URL" -X POST "$API/auth/logout" -o /dev/null
echo "== OK — smoke de solo lectura completado, nada escrito en producción =="
