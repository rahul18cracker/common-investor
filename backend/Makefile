# Common Investor Backend - Test & Development Commands

.PHONY: help test test-unit test-integration test-e2e test-fast test-coverage test-watch clean lint format

# Default target
help:
	@echo "Common Investor Backend - Available Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run only unit tests (fast)"
	@echo "  make test-integration  - Run integration tests"
	@echo "  make test-e2e          - Run end-to-end tests"
	@echo "  make test-fast         - Run fast tests only (exclude slow)"
	@echo "  make test-coverage     - Run tests with HTML coverage report"
	@echo "  make test-watch        - Run tests in watch mode"
	@echo "  make test-migration    - Run migration tests only"
	@echo "  make test-api          - Run API endpoint tests only"
	@echo "  make test-celery       - Run Celery worker tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              - Run code linters"
	@echo "  make format            - Format code with black/isort"
	@echo "  make type-check        - Run type checking with mypy"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Remove test artifacts and cache"
	@echo ""
	@echo "Development:"
	@echo "  make install           - Install dependencies"
	@echo "  make dev               - Start development server"

# ==========================================
# Testing Commands
# ==========================================

test:
	@echo "Running all tests..."
	pytest -v

test-unit:
	@echo "Running unit tests..."
	pytest -v -m unit

test-integration:
	@echo "Running integration tests..."
	pytest -v -m integration

test-e2e:
	@echo "Running end-to-end tests..."
	pytest -v -m e2e

test-fast:
	@echo "Running fast tests (excluding slow)..."
	pytest -v -m "not slow"

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"
	@echo "Open with: open htmlcov/index.html (macOS) or xdg-open htmlcov/index.html (Linux)"

test-watch:
	@echo "Running tests in watch mode..."
	pytest-watch -v

test-migration:
	@echo "Running migration tests..."
	pytest -v -m migration

test-api:
	@echo "Running API endpoint tests..."
	pytest -v -m api

test-celery:
	@echo "Running Celery worker tests..."
	pytest -v -m celery

test-db:
	@echo "Running database tests..."
	pytest -v -m db

test-verbose:
	@echo "Running tests with verbose output..."
	pytest -vvs

test-debug:
	@echo "Running tests with debugger on failure..."
	pytest --pdb -x

test-failed:
	@echo "Re-running only failed tests..."
	pytest --lf

test-parallel:
	@echo "Running tests in parallel..."
	pytest -n auto

# ==========================================
# Code Quality
# ==========================================

lint:
	@echo "Running linters..."
	flake8 app/ tests/
	pylint app/ tests/

format:
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/

type-check:
	@echo "Running type checker..."
	mypy app/

check-all: lint type-check test
	@echo "All checks passed!"

# ==========================================
# Cleanup
# ==========================================

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .coverage coverage.xml 2>/dev/null || true
	@echo "Cleanup complete!"

# ==========================================
# Development
# ==========================================

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements.txt
	pip install black flake8 pylint mypy isort pytest-watch

dev:
	@echo "Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# ==========================================
# Docker Commands
# ==========================================

docker-test:
	@echo "Running tests in Docker..."
	docker compose exec api pytest -v

docker-coverage:
	@echo "Running coverage in Docker..."
	docker compose exec api pytest --cov=app --cov-report=html

docker-shell:
	@echo "Opening shell in API container..."
	docker compose exec api bash

# ==========================================
# CI/CD Commands
# ==========================================

ci-test:
	@echo "Running CI test suite..."
	pytest -v --cov=app --cov-report=xml --cov-report=term --cov-fail-under=80

ci-lint:
	@echo "Running CI linting..."
	flake8 app/ tests/ --max-line-length=120

# ==========================================
# Database Commands
# ==========================================

db-migrate:
	@echo "Running database migrations..."
	alembic upgrade head

db-rollback:
	@echo "Rolling back last migration..."
	alembic downgrade -1

db-revision:
	@echo "Creating new migration..."
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# ==========================================
# Information
# ==========================================

info:
	@echo "Backend Information"
	@echo "==================="
	@echo "Python: $$(python --version)"
	@echo "Pytest: $$(pytest --version)"
	@echo "Tests: $$(find tests -name 'test_*.py' | wc -l | tr -d ' ') files"
	@echo "Coverage: Run 'make test-coverage' to see"
