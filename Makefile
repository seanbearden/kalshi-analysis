.PHONY: help demo up down logs clean install-backend install-frontend migrate test

help: ## Show this help message
	@echo "Kalshi Market Insights - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

demo: ## Start all services (one-click launch)
	docker compose up -d
	@echo "✅ Services starting..."
	@echo "📊 Frontend: http://localhost:5173"
	@echo "🔧 Backend API: http://localhost:8000/docs"
	@echo ""
	@echo "Run 'make logs' to view logs"

up: ## Start all services in foreground
	docker compose up

down: ## Stop all services
	docker compose down

logs: ## View logs from all services
	docker compose logs -f

clean: ## Stop services and remove volumes
	docker compose down -v
	@echo "✅ All services stopped and volumes removed"

install-backend: ## Install backend dependencies locally
	cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies locally
	cd frontend && pnpm install

migrate: ## Run database migrations
	docker compose exec api alembic upgrade head

test: ## Run backend tests
	docker compose exec api pytest

format: ## Format code (black, ruff)
	cd backend && black . && ruff check --fix .

lint: ## Lint code (ruff, mypy)
	cd backend && ruff check . && mypy .
