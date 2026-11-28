PORT ?= 8000
SERVICES = auth order courier tracking

.PHONY: help test docker-test up down logs ps smoke resilience clean config $(addprefix run-,$(SERVICES))

help: ## Buyruqlar ro‘yxati
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

test: ## Unit va integratsion testlar (Docker’siz, SQLite + xotiradagi shina)
	python3 -m unittest discover -s tests -v

docker-test: ## Testlarni Docker ichida ishlatish
	docker build --target test --tag crystal-logistics:test .

config: ## compose.yaml’ni tekshirish
	docker compose config --quiet

up: ## Butun stack’ni ko‘tarish (3 servis, 3 PostgreSQL, RabbitMQ, gateway)
	docker compose up --build --detach --wait --wait-timeout 180

down: ## To‘xtatish (ma’lumotlar saqlanadi)
	docker compose down

logs: ## Barcha servis loglari
	docker compose logs --follow order-service courier-service tracking-service gateway

ps: ## Konteynerlar holati
	docker compose ps

smoke: ## Gateway orqali to‘liq hayot sikli
	./scripts/smoke_test.sh http://localhost:$(PORT)

resilience: ## Izolyatsiya, outbox va saqlanish testlari
	./scripts/resilience_test.sh http://localhost:$(PORT)

clean: ## Konteyner va volume’larni o‘chirish (MA’LUMOTLAR O‘CHADI)
	docker compose down --volumes

run-%: ## Bitta servisni lokal ishga tushirish (masalan: make run-order)
	PYTHONPATH=services/common:services/$* python3 -m $*_service
