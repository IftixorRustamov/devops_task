#!/usr/bin/env bash
# Gateway orqali butun tizimni tekshiradi: 4 servis, 4 baza, RabbitMQ, JWT va rollar.
# Foydalanish: ./scripts/smoke_test.sh [BASE_URL]
# Admin paroli: CRYSTAL_ADMIN_PASSWORD (standart — .env.example dagi lokal parol).
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
ADMIN_USER="${CRYSTAL_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${CRYSTAL_ADMIN_PASSWORD:-admin_dev_password}"
SUFFIX=$(date +%s)
TOKEN=""

# call METHOD PATH BODY EXPECTED_STATUS  (TOKEN o‘zgaruvchisi bo‘lsa Bearer sifatida yuboriladi)
call() {
  local method="$1" path="$2" body="${3:-}" expected="$4" response status
  local args=(-sS -w '\n%{http_code}' -X "$method")
  [[ -n "$TOKEN" ]] && args+=(-H "Authorization: Bearer $TOKEN")
  [[ -n "$body" ]] && args+=(-H 'Content-Type: application/json' --data "$body")
  response=$(curl "${args[@]}" "${EXTRA_HEADERS[@]}" "$BASE_URL$path")
  status="${response##*$'\n'}"
  BODY="${response%$'\n'*}"
  if [[ "$status" != "$expected" ]]; then
    echo "XATO: $method $path -> $status (kutilgan $expected): $BODY" >&2
    exit 1
  fi
  echo "OK   $method $path -> $status${TOKEN:+  [${WHO:-?}]}"
}
EXTRA_HEADERS=()
json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

login() {  # login USER PASS -> TOKEN, REFRESH
  TOKEN=""
  call POST /api/v1/auth/login "{\"username\":\"$1\",\"password\":\"$2\"}" 200
  TOKEN=$(printf '%s' "$BODY" | json 'd["access_token"]')
  REFRESH=$(printf '%s' "$BODY" | json 'd["refresh_token"]')
  WHO="$1"
}

echo "== sog‘liq"
call GET /health "" 200
for service in auth order courier tracking; do
  call GET "/health/$service" "" 200
  printf '%s' "$BODY" | json 'd["checks"]["database"]' | grep -qx ok
done

curl -fsS "$BASE_URL/" | grep -q "Crystal Logistics" && echo "OK   GET / -> namoyish sahifasi"

echo "== autentifikatsiya"
call POST /api/v1/orders '{"address": "x"}' 401                     # token yo‘q
EXTRA_HEADERS=(-H 'X-User: admin' -H 'X-User-Role: admin')
call POST /api/v1/orders '{"address": "x"}' 401                     # soxta sarlavha yordam bermaydi
EXTRA_HEADERS=()
TOKEN="buzilgan.token.qiymat"; call GET /api/v1/auth/me "" 401; TOKEN=""
call POST /api/v1/auth/login '{"username":"admin","password":"noto‘g‘ri-parol"}' 401

login "$ADMIN_USER" "$ADMIN_PASS"
OPERATOR="op_$SUFFIX"; COURIER="ali_$SUFFIX"; OTHER="vali_$SUFFIX"
call POST /api/v1/auth/users "{\"username\":\"$OPERATOR\",\"password\":\"smoke-parol-1\",\"role\":\"operator\"}" 201
call POST /api/v1/auth/users "{\"username\":\"$COURIER\",\"password\":\"smoke-parol-1\",\"role\":\"courier\"}" 201
call POST /api/v1/auth/users "{\"username\":\"$OTHER\",\"password\":\"smoke-parol-1\",\"role\":\"courier\"}" 201
call GET /api/v1/auth/users "" 200

echo "== buyurtma hayot sikli (operator)"
login "$OPERATOR" smoke-parol-1
call GET /api/v1/auth/me "" 200
call GET /api/v1/auth/users "" 403                                   # faqat admin
call GET /api/v1/warehouses "" 200
call POST /api/v1/orders '{"address": "Smoke manzil"}' 201
CODE=$(printf '%s' "$BODY" | json 'd["code"]')
call POST "/api/v1/orders/$CODE/receive" "" 200
call POST "/api/v1/orders/$CODE/dispatch" "" 409                     # kuryer hali yo‘q
call POST "/api/v1/orders/$CODE/assign" '{"courier": "begona_kuryer"}' 400
call POST "/api/v1/orders/$CODE/assign" "{\"courier\": \"$COURIER\"}" 200
call POST "/api/v1/orders/$CODE/assign" "{\"courier\": \"$OTHER\"}" 409
call POST "/api/v1/orders/$CODE/dispatch" "" 200

echo "== kuryerlar"
login "$OTHER" smoke-parol-1
call POST /api/v1/orders '{"address": "x"}' 403                     # kuryer buyurtma yarata olmaydi
call POST "/api/v1/orders/$CODE/deliver" "" 403                      # unga biriktirilmagan
login "$COURIER" smoke-parol-1
call GET /api/v1/couriers/me/assignments "" 200
printf '%s' "$BODY" | json '[i["code"] for i in d["items"]]' | grep -q "$CODE"
call POST "/api/v1/orders/$CODE/deliver" "" 200
call POST "/api/v1/orders/$CODE/deliver" "" 409
call GET "/api/v1/orders/$CODE" "" 200
printf '%s' "$BODY" | json 'd["status"]' | grep -qx 'Yetkazildi'

echo "== refresh va logout"
OLD_REFRESH="$REFRESH"; TOKEN=""
call POST /api/v1/auth/refresh "{\"refresh_token\":\"$OLD_REFRESH\"}" 200
NEW_REFRESH=$(printf '%s' "$BODY" | json 'd["refresh_token"]')
call POST /api/v1/auth/refresh "{\"refresh_token\":\"$OLD_REFRESH\"}" 401   # qayta ishlatish rad etiladi
call POST /api/v1/auth/refresh "{\"refresh_token\":\"$NEW_REFRESH\"}" 401   # ...va sessiya bekor qilindi

echo "== xatolar va ichki API"
login "$OPERATOR" smoke-parol-1
call GET /api/v1/orders/CRY-UNKNOWN "" 404
call GET "/internal/orders/$CODE" "" 404                            # ichki API tashqariga yopiq
call GET "/internal/verify" "" 404
TOKEN=""

echo "== ommaviy kuzatuv (token kerak emas)"
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
if printf '%s' "$BODY" | grep -qE "Smoke|$COURIER"; then
  echo "XATO: kuzatuv javobida shaxsiy ma’lumot bor: $BODY" >&2; exit 1
fi
echo "OK   tracking-service hodisalar orqali yangilandi"

echo "Smoke test muvaffaqiyatli: $CODE"
