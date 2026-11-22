#!/usr/bin/env bash
# Mikroservis kafolatlarini docker compose stack’ida tekshiradi:
#  1. Database-per-service: servis boshqa servis bazasini tarmoqda ham ko‘rmaydi.
#  2. Outbox: RabbitMQ o‘chib turganda ham buyurtma yaratiladi, hodisa keyin yetib boradi.
#  3. Ma’lumotlar konteynerlar qayta ishga tushgandan keyin saqlanadi.
# Foydalanish: ./scripts/resilience_test.sh [BASE_URL]
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
can_resolve() {  # $1 = servis, $2 = host
  docker compose exec -T "$1" python -c "import socket,sys; socket.getaddrinfo('$2', 5432)" 2>/dev/null
}

echo "== 1. Bazalar izolyatsiyasi"
can_resolve order-service order-db || { echo "XATO: order-service o‘z bazasini ko‘rmayapti" >&2; exit 1; }
for pair in "order-service courier-db" "order-service tracking-db" "courier-service order-db" \
            "courier-service tracking-db" "tracking-service order-db" "tracking-service courier-db"; do
  set -- $pair
  if can_resolve "$1" "$2"; then
    echo "XATO: $1 $2 ga ulana oladi — izolyatsiya buzilgan" >&2; exit 1
  fi
  echo "OK   $1 -/-> $2"
done

echo "== 2. RabbitMQ o‘chganda outbox"
docker compose stop rabbitmq
CODE=$(curl -fsS -X POST -H 'Content-Type: application/json' --data '{"address":"Outbox"}' \
  "$BASE_URL/api/v1/orders" | json 'd["code"]')
echo "OK   broker yo‘q, lekin buyurtma yaratildi: $CODE"
curl -fsS "$BASE_URL/health/order" | json 'd["status"]' | grep -qx degraded
echo "OK   order-service holati: degraded (bazasi ishlaydi, broker yo‘q)"
docker compose start rabbitmq
docker compose up --detach --wait --wait-timeout 120 rabbitmq
for _ in $(seq 1 90); do
  if curl -fsS "$BASE_URL/api/v1/tracking/$CODE" >/dev/null 2>&1; then
    echo "OK   broker qaytgach hodisa tracking-service’ga yetib bordi"
    break
  fi
  sleep 1
done
curl -fsS "$BASE_URL/api/v1/tracking/$CODE" >/dev/null \
  || { echo "XATO: hodisa yetib bormadi" >&2; exit 1; }

echo "== 3. Qayta ishga tushirishdan keyin ma’lumot saqlanadi"
docker compose restart order-service courier-service tracking-service order-db courier-db tracking-db
docker compose up --detach --wait --wait-timeout 180
# Gateway qayta yaratilgan servislarning YANGI manzillariga yo‘naltirishi kerak.
for route in "/api/v1/orders/$CODE order-service" "/api/v1/tracking/$CODE tracking-service" \
             "/health/courier courier-service"; do
  set -- $route
  served_by=$(curl -sS -o /dev/null -D - "$BASE_URL$1" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-service"{print $2}')
  [[ "$served_by" == "$2" ]] || { echo "XATO: $1 -> '$served_by' javob berdi (kutilgan $2)" >&2; exit 1; }
  echo "OK   $1 -> $served_by"
done
curl -fsS "$BASE_URL/api/v1/orders/$CODE" | json 'd["status"]' | grep -qx Yangi
curl -fsS "$BASE_URL/api/v1/tracking/$CODE" | json 'd["status"]' | grep -qx Yangi
echo "OK   buyurtma va kuzatuv ma’lumoti saqlangan"

echo "Resilience test muvaffaqiyatli"
