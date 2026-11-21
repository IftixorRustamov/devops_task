#!/usr/bin/env bash
# Ishlayotgan API’da buyurtmaning to‘liq hayot siklini tekshiradi.
# Foydalanish: ./scripts/smoke_test.sh [BASE_URL]
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

call() {
  local method="$1" path="$2" body="${3:-}" expected="$4" response status
  if [[ -n "$body" ]]; then
    response=$(curl -sS -w '\n%{http_code}' -X "$method" -H 'Content-Type: application/json' \
      --data "$body" "$BASE_URL$path")
  else
    response=$(curl -sS -w '\n%{http_code}' -X "$method" "$BASE_URL$path")
  fi
  status="${response##*$'\n'}"
  BODY="${response%$'\n'*}"
  if [[ "$status" != "$expected" ]]; then
    echo "XATO: $method $path -> $status (kutilgan $expected): $BODY" >&2
    exit 1
  fi
  echo "OK   $method $path -> $status"
}

call GET /health "" 200
call POST /api/v1/orders '{"address": "Smoke manzil"}' 201
CODE=$(printf '%s' "$BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["code"])')
call POST "/api/v1/orders/$CODE/receive" "" 200
call POST "/api/v1/orders/$CODE/assign" '{"courier": "Smoke kuryer"}' 200
call POST "/api/v1/orders/$CODE/dispatch" "" 200
call POST "/api/v1/orders/$CODE/deliver" "" 200
call GET "/api/v1/orders/$CODE" "" 200
printf '%s' "$BODY" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["status"]=="Yetkazildi", d'
call POST "/api/v1/orders/$CODE/deliver" "" 409
call GET /api/v1/orders/CRY-UNKNOWN "" 404

echo "Smoke test muvaffaqiyatli: $CODE"
