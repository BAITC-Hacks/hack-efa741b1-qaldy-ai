.PHONY: up down test-api check-web

up:
	docker compose up --build

down:
	docker compose down

test-api:
	cd apps/api && pytest

check-web:
	cd apps/web && npm run typecheck && npm run build
