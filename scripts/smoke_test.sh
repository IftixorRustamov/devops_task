#!/usr/bin/env bash
# Gateway orqali butun tizimni tekshiradi: 3 servis, 3 baza, RabbitMQ hodisalari.
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

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

call GET /health "" 200
for service in order courier tracking; do
  call GET "/health/$service" "" 200
  printf '%s' "$BODY" | json 'd["checks"]["database"]' | grep -qx ok
done

call GET /api/v1/warehouses "" 200
call POST /api/v1/orders '{"address": "Smoke manzil"}' 201
CODE=$(printf '%s' "$BODY" | json 'd["code"]')
call POST "/api/v1/orders/$CODE/receive" "" 200
call POST "/api/v1/orders/$CODE/dispatch" "" 409          # kuryer hali yo‘q
call POST "/api/v1/orders/$CODE/assign" '{"courier": "Smoke kuryer"}' 200
call POST "/api/v1/orders/$CODE/assign" '{"courier": "Boshqa"}' 409
call POST "/api/v1/orders/$CODE/dispatch" "" 200
call POST "/api/v1/orders/$CODE/deliver" "" 200
call GET "/api/v1/orders/$CODE" "" 200
printf '%s' "$BODY" | json 'd["status"]' | grep -qx 'Yetkazildi'
call POST "/api/v1/orders/$CODE/deliver" "" 409
call GET /api/v1/orders/CRY-UNKNOWN "" 404
call GET "/internal/orders/$CODE" "" 404                   # ichki API tashqariga yopiq

# tracking-service hodisalardan quriladi (eventual consistency) — 15 s gacha kutamiz.
for _ in $(seq 1 30); do
  status=$(curl -sS -o /tmp/crystal-track.json -w '%{http_code}' "$BASE_URL/api/v1/tracking/$CODE")
  if [[ "$status" == 200 ]] && json 'd["status"]' < /tmp/crystal-track.json | grep -qx 'Yetkazildi'; then
    break
  fi
  sleep 0.5
done
call GET "/api/v1/tracking/$CODE" "" 200
printf '%s' "$BODY" | json 'd["status"]' | grep -qx 'Yetkazildi' \
  || { echo "XATO: tracking-service hodisalarni olmadi: $BODY" >&2; exit 1; }
printf '%s' "$BODY" | json 'd["courier_assigned"]' | grep -qx True
if printf '%s' "$BODY" | grep -q 'Smoke'; then
  echo "XATO: kuzatuv javobida shaxsiy ma’lumot bor: $BODY" >&2; exit 1
fi
echo "OK   tracking-service hodisalar orqali yangilandi"

echo "Smoke test muvaffaqiyatli: $CODE"
