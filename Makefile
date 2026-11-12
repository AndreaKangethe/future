.PHONY: up down logs test seed migrate lint reset
up:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build -d
down:
	docker compose down
logs:
	docker compose logs -f --tail=100
test:
	docker compose run --rm backend pytest
seed:
	docker compose --profile demo run --rm seed
migrate:
	docker compose exec backend python -m app.bootstrap
lint:
	docker compose run --rm backend ruff check app tests
reset:
	docker compose down -v
