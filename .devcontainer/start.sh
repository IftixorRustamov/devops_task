#!/usr/bin/env bash
# Codespace har safar ishga tushganda: stack’ni ko‘taradi va ommaviy manzilni ko‘rsatadi.
set -uo pipefail
cd "$(dirname "$0")/.."

echo "Crystal Logistics ishga tushirilmoqda (birinchi marta 3–5 daqiqa)…"
for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 2; done

if docker compose up --build --detach --wait --wait-timeout 300; then
  if [[ -n "${CODESPACE_NAME:-}" ]]; then
    # 8000 portni ommaviy qilish — o‘qituvchi GitHub akkauntisiz ochishi uchun.
    gh codespace ports visibility 8000:public -c "$CODESPACE_NAME" >/dev/null 2>&1 || true
    URL="https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  else
    URL="http://localhost:8000"
  fi
  echo "$URL" > .devcontainer/url.txt
  echo
  echo "Tayyor! Namoyish sahifasi: $URL"
  echo "  To‘liq tekshiruv:  ./scripts/smoke_test.sh"
  echo "  Agar havola o‘qituvchida ochilmasa: PORTS oynasi -> 8000 -> o‘ng tugma -> Port Visibility -> Public"
else
  echo "Stack ko‘tarilmadi. Loglar: docker compose logs --tail 50" >&2
fi
