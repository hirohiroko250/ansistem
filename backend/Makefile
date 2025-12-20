# OZA System Makefile

.PHONY: help install dev run test migrate makemigrations shell superuser docker-up docker-down docker-build docker-logs clean check logcheck

help:
	@echo "OZA System Backend Commands"
	@echo ""
	@echo "Development:"
	@echo "  install        Install dependencies"
	@echo "  dev            Run development server"
	@echo "  run            Run production server"
	@echo "  test           Run tests"
	@echo "  lint           Run linting"
	@echo ""
	@echo "Database:"
	@echo "  migrate        Apply migrations"
	@echo "  makemigrations Create new migrations"
	@echo "  shell          Django shell"
	@echo "  superuser      Create superuser"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up      Start Docker containers"
	@echo "  docker-down    Stop Docker containers"
	@echo "  docker-build   Build Docker images"
	@echo "  docker-logs    View Docker logs"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          Clean up cache files"
	@echo "  check          Run all checks (Django, migrations, tests)"
	@echo "  logcheck       Run checks and save log to docs/debug/"

# Development
install:
	pip install -r requirements/development.txt

dev:
	python manage.py runserver --settings=config.settings.development

run:
	gunicorn --bind 0.0.0.0:8000 --workers 4 config.wsgi:application

test:
	pytest -v --cov=apps --cov-report=html

lint:
	flake8 apps
	black --check apps
	isort --check-only apps

format:
	black apps
	isort apps

# Database
migrate:
	python manage.py migrate --settings=config.settings.development

makemigrations:
	python manage.py makemigrations --settings=config.settings.development

shell:
	python manage.py shell_plus --settings=config.settings.development

superuser:
	python manage.py createsuperuser --settings=config.settings.development

# Docker Development
docker-up:
	docker-compose -f docker-compose.dev.yml up -d

docker-down:
	docker-compose -f docker-compose.dev.yml down

docker-build:
	docker-compose -f docker-compose.dev.yml build

docker-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Docker Production
docker-prod-up:
	docker-compose up -d

docker-prod-down:
	docker-compose down

docker-prod-build:
	docker-compose build

docker-prod-logs:
	docker-compose logs -f

# Utilities
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete

# Check & Debug
check:
	@echo "=== Running Django System Check ==="
	docker-compose exec backend python manage.py check --settings=config.settings.development || true
	@echo ""
	@echo "=== Running Migrations Check ==="
	docker-compose exec backend python manage.py makemigrations --check --dry-run --settings=config.settings.development || true
	@echo ""
	@echo "=== Running Tests ==="
	docker-compose exec backend pytest -v --tb=short || true
	@echo ""
	@echo "=== Container Status ==="
	docker-compose ps

logcheck:
	@cd .. && bash tools/logrun.sh "cd backend && make check"
