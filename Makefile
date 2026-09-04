#!/usr/bin/env make
# DT-Lite V4.0 Makefile

.PHONY: install dev test build clean db-migrate db-seed help

.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "Installing Python dependencies..."
	@for svc in services/*/; do \
		if [ -f "$$svc/requirements.txt" ]; then \
			cd "$$svc" && pip install -r requirements.txt; \
		fi; \
	done

dev: ## Start development environment with Docker Compose
	@docker compose up -d
	@echo ""
	@echo "=== DT-Lite V4.0 Dev Environment ==="
	@echo "Frontend Web:    http://localhost:3000"
	@echo "Frontend Admin:  http://localhost:3001"
	@echo "Gateway API:     http://localhost:8000/docs"
	@echo "EMQX Dashboard:  http://localhost:18083"
	@echo "MinIO Console:   http://localhost:9001"
	@echo "==================================="

test: ## Run all tests
	@echo "Running tests..."
	@for svc in services/*/; do \
		if [ -d "$$svc/tests" ]; then \
			cd "$$svc" && python -m pytest tests/ -v; \
		fi; \
	done

build: ## Build all Docker images
	@docker compose build
	@echo "Build complete."

clean: ## Clean up containers and volumes
	@docker compose down -v --remove-orphans
	@echo "Cleaned up."

db-migrate: ## Run database migrations
	@echo "Running Alembic migrations..."
	@cd services/core && alembic upgrade head

db-seed: ## Seed database with sample data
	@echo "Seeding database..."
	@cd database/seeds && python seed.py

logs: ## Show service logs
	@docker compose logs -f

ps: ## List running services
	@docker compose ps

down: ## Stop all services
	@docker compose down

status: ## Check service health
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "Gateway: DOWN"
	@curl -s http://localhost:8001/health || echo "Identity: DOWN"
	@curl -s http://localhost:8002/health || echo "Core: DOWN"
	@curl -s http://localhost:8003/health || echo "Twin: DOWN"
