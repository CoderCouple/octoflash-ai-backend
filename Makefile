.PHONY: help install dev run test lint format clean migrate docker-up docker-down docker-build docker-logs docker-db worker

help:
	@echo "Available commands:"
	@echo "  install       Install dependencies"
	@echo "  dev           Run development server"
	@echo "  run           Run production server"
	@echo "  worker        Run RQ render worker"
	@echo "  test          Run tests"
	@echo "  lint          Run linters"
	@echo "  format        Format code"
	@echo "  clean         Clean cache files"
	@echo "  migrate       Run database migrations"
	@echo ""
	@echo "Docker commands:"
	@echo "  docker-up     Start all services"
	@echo "  docker-down   Stop all services"
	@echo "  docker-build  Build and start all services"
	@echo "  docker-logs   Tail logs"
	@echo "  docker-db     Start only PostgreSQL + pgAdmin"

install:
	poetry install

dev:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

worker:
	poetry run python -m app.workers.worker

# Live preview a template — no API / Temporal / DB involved.
#   make preview T=title_reveal
#   make preview T=text_pop ARGS='--param text=\"Hi\" --style manic'
preview:
	@test -n "$(T)" || (echo "Usage: make preview T=<template_id> [ARGS='--param k=v ...']" && exit 1)
	poetry run python scripts/preview_template.py $(T) $(ARGS)

# Convenience: run worker against the Temporal CLI's "cloud" profile.
# Set up once with: temporal --profile cloud config set --prop ...
worker-cloud:
	TEMPORAL_PROFILE=cloud poetry run python -m app.workers.worker

test:
	poetry run pytest tests/ -v

lint:
	poetry run ruff check .
	poetry run mypy app/

format:
	poetry run black .
	poetry run isort .
	poetry run ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

migrate:
	poetry run alembic upgrade head

migration:
	@test -n "$(MSG)" || (echo "Usage: make migration MSG='description'" && exit 1)
	poetry run alembic revision --autogenerate -m "$(MSG)"

pre-commit:
	poetry run pre-commit install

pre-commit-run:
	poetry run pre-commit run --all-files

# Docker commands
docker-up:
	docker-compose up

docker-down:
	docker-compose down

docker-build:
	docker-compose up --build

docker-logs:
	docker-compose logs -f

docker-db:
	docker-compose up db pgadmin
