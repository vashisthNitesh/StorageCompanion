.PHONY: help up down restart logs migrate migrations test test-backend test-frontend seed lint dev-backend dev-frontend build-frontend

help:
	@echo "SpeedCloud Development Commands:"
	@echo "  make up              Start local services (Postgres, Redis, MinIO)"
	@echo "  make down            Stop local services"
	@echo "  make migrate         Run Django database migrations"
	@echo "  make migrations      Create new Django migrations"
	@echo "  make dev-backend     Run Django dev server"
	@echo "  make dev-frontend    Run Vite frontend dev server"
	@echo "  make test            Run backend and frontend tests"
	@echo "  make seed            Seed demo plans and sample accounts"
	@echo "  make build-frontend  Compile frontend for production"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	backend/.venv/bin/python backend/manage.py migrate

migrations:
	backend/.venv/bin/python backend/manage.py makemigrations

dev-backend:
	backend/.venv/bin/python backend/manage.py runserver 0.0.0.0:8000

dev-frontend:
	npm --prefix frontend run dev

build-frontend:
	npm --prefix frontend run build

test-backend:
	backend/.venv/bin/pytest backend/tests/

test-frontend:
	npm --prefix frontend test

test: test-backend test-frontend

seed:
	backend/.venv/bin/python backend/manage.py seed_demo

lint:
	backend/.venv/bin/ruff check backend/
	npm --prefix frontend run lint
