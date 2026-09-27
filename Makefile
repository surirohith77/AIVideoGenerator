.PHONY: help setup dev build test migrate clean

help:
	@echo "AI Video Studio (AivideoGeneration) Development Commands:"
	@echo "  make setup     - Install backend & frontend dependencies"
	@echo "  make dev       - Run development services (backend + frontend)"
	@echo "  make docker-up - Start Docker services (PostgreSQL, Redis)"
	@echo "  make test      - Run backend unit and integration tests"
	@echo "  make migrate   - Run database migrations"

setup:
	cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
	cd frontend && npm install

docker-up:
	docker compose up -d postgres redis

dev-backend:
	cd backend && ./venv/bin/uvicorn app.main:app --reload --port 8000

dev-worker:
	cd backend && ./venv/bin/celery -A app.workers.celery_worker worker --loglevel=info

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && ./venv/bin/pytest -v tests/

migrate:
	cd backend && ./venv/bin/alembic upgrade head
