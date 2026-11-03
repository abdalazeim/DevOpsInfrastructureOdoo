# ==============================================================================
# Makefile — Django Enterprise Starter (Docker)
# Run from deployment/docker/ directory
# ==============================================================================

.PHONY: help build up down restart logs shell migrate makemigrations \
        createsuperuser collectstatic test lint format clean

SHELL := /bin/bash
DC := docker compose

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Development (run from deployment/docker/) ─────────────────────

build: ## Build Docker images
	$(DC) build

up: ## Start all services
	$(DC) up -d

down: ## Stop all services
	$(DC) down

restart: ## Restart all services
	$(DC) restart

logs: ## View logs (usage: make logs s=django)
	$(DC) logs -f $(s)

ps: ## Show running services
	$(DC) ps

shell: ## Open Django shell
	$(DC) exec django python manage.py shell

migrate: ## Run database migrations
	$(DC) exec django python manage.py migrate --noinput

makemigrations: ## Create new migrations
	$(DC) exec django python manage.py makemigrations

createsuperuser: ## Create admin user
	$(DC) exec django python manage.py createsuperuser

collectstatic: ## Collect static files
	$(DC) exec django python manage.py collectstatic --noinput --clear

dbshell: ## Open database shell
	$(DC) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

test: ## Run tests with coverage
	$(DC) exec django coverage run -m pytest
	$(DC) exec django coverage report

lint: ## Run ruff (check + format)
	$(DC) exec django ruff check .
	$(DC) exec django ruff format --check .

format: ## Format code (ruff)
	$(DC) exec django ruff check --fix .
	$(DC) exec django ruff format .

check: ## Check formatting (CI mode)
	$(DC) exec django ruff format --check .
	$(DC) exec django ruff check .

clean: ## Remove all Docker artifacts
	$(DC) down -v --remove-orphans
	docker system prune -f

# ─── Production (run from PROJECT ROOT, parent of deployment/) ─────

prod-build: ## Build production image (run from project root)
	cd ../.. && $(DC) -f deployment/docker/docker-compose.prod.yml build

prod-up: ## Start production services (run from project root)
	cd ../.. && $(DC) -f deployment/docker/docker-compose.prod.yml up -d

prod-down: ## Stop production services
	cd ../.. && $(DC) -f deployment/docker/docker-compose.prod.yml down
