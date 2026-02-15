.PHONY: help install test lint format clean docker-up docker-down

# Default target
help:
	@echo "Available commands:"
	@echo "  install       Install all dependencies"
	@echo "  test          Run all unit tests"
	@echo "  test-int      Run integration tests"
	@echo "  lint          Run all linters"
	@echo "  format        Auto-format code"
	@echo "  clean         Remove build artifacts"
	@echo "  docker-up     Start local dev services"
	@echo "  docker-down   Stop local dev services"
	@echo "  dbt-run       Run all dbt models"
	@echo "  dbt-test      Run all dbt tests"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

test:
	pytest tests/unit -m "not slow" -v

test-all:
	pytest tests/ -v

test-int:
	pytest tests/integration -v

lint:
	flake8 ingestion/ processing/ orchestration/ data_quality/ tests/
	mypy ingestion/ processing/ --ignore-missing-imports
	isort --check-only --diff .

format:
	black ingestion/ processing/ orchestration/ data_quality/ tests/
	isort ingestion/ processing/ orchestration/ data_quality/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "✅ Services ready: Kafka (9092), Postgres (5432), Airflow (8080)"

docker-down:
	docker-compose down

dbt-run:
	cd dbt && dbt run

dbt-test:
	cd dbt && dbt test

dbt-docs:
	cd dbt && dbt docs generate && dbt docs serve

spark-job:
	python processing/spark/jobs/$(JOB).py

validate-dags:
	pytest orchestration/tests/test_dag_validation.py -v
