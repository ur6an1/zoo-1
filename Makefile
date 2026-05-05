.PHONY: up down logs migrate migration test lint build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

test:
	docker compose run --rm backend pytest --cov --cov-fail-under=75

lint:
	ruff check .

build:
	docker compose build
