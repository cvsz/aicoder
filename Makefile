.PHONY: install install-dev test test-cov lint format typecheck security check run docker-build docker-run health clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest

test-cov:
	pytest --cov --cov-report=term-missing

lint:
	ruff check .

format:
	black .

typecheck:
	mypy . --ignore-missing-imports

security:
	bandit -r . -x ./tests

check: lint typecheck security test-cov

run:
	python main.py

health:
	python main.py --health-check

docker-build:
	docker build -t zcoder:latest .

docker-run:
	docker run --rm -e ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} zcoder:latest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml dist build
