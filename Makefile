.PHONY: help migrate migrations test test-backend test-frontend seed lint dev-backend dev-frontend build-frontend

help:
	@echo "SmartSpace development commands:"
	@echo "  make migrate         Run Django database migrations"
	@echo "  make migrations      Create new Django migrations"
	@echo "  make dev-backend     Run Django dev server on :8000"
	@echo "  make dev-frontend    Run Vite dev server on :5173 (proxies /api to :8000)"
	@echo "  make test            Run backend and frontend tests"
	@echo "  make seed            Create or update subscription plans"
	@echo "  make build-frontend  Compile frontend for production"

migrate:
	backend/.venv/bin/python backend/manage.py migrate

migrations:
	backend/.venv/bin/python backend/manage.py makemigrations

dev-backend:
	backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8000

dev-frontend:
	npm --prefix frontend run dev

build-frontend:
	npm --prefix frontend run build

# Tests always run against an in-memory SQLite database (config.settings.test).
test-backend:
	cd backend && .venv/bin/pytest

test-frontend:
	npm --prefix frontend test

test: test-backend test-frontend

seed:
	backend/.venv/bin/python backend/manage.py seed_plans

lint:
	backend/.venv/bin/ruff check backend/
	npm --prefix frontend run build
