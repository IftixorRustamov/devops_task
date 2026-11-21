IMAGE ?= crystal-logistics
PORT  ?= 8000

.PHONY: help test run demo docker-test docker-build up down logs ps smoke clean

help: ## Buyruqlar ro‘yxati
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

test: ## Testlarni lokal ishlatish
	python3 -m unittest discover -s tests -v

run: ## API’ni lokal ishga tushirish (Docker’siz)
	python3 -m crystal serve --port $(PORT)

demo: ## Demo buyurtma hayot sikli
	python3 -m crystal demo

docker-test: ## Testlarni Docker ichida ishlatish
	docker build --target test --tag $(IMAGE):test .

docker-build: ## Ishchi obrazni yig‘ish
	docker build --target runtime --tag $(IMAGE) .

up: ## docker compose bilan ishga tushirish
	docker compose up --build --detach --wait

down: ## Konteynerlarni to‘xtatish (ma’lumotlar saqlanadi)
	docker compose down

logs: ## Loglarni kuzatish
	docker compose logs --follow api

ps: ## Konteyner holati
	docker compose ps

smoke: ## Ishlayotgan API’ni tekshirish
	./scripts/smoke_test.sh http://localhost:$(PORT)

clean: ## Konteyner va volume’ni o‘chirish (MA’LUMOTLAR O‘CHADI)
	docker compose down --volumes
