.PHONY: install install-dev test test-cov lint format typecheck security check run docker-build docker-run health clean build build-windows build-linux installer

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	HOME=$(CURDIR)/.test-home pytest

test-cov:
	pytest --cov --cov-report=term-missing

lint:
	ruff check .

format:
	black .

typecheck:
	mypy . --ignore-missing-imports --explicit-package-bases

security:
	bandit -r . -x ./tests

check: lint typecheck security test-cov

run:
	python main.py

tui:
	python main.py --tui

health:
	python main.py --health-check

# ── Build targets ────────────────────────────────────────────────────────

build: build-linux

build-linux:
	@echo "Building Linux executable..."
	pip install pyinstaller
	pyinstaller zai-coder.spec --noconfirm --clean
	@echo "Output: dist/zai-coder"

build-windows:
	@echo "Building Windows executable..."
	@echo "Run on Windows: powershell -ExecutionPolicy Bypass -File build-windows.ps1"
	@echo "Or: build.bat"

installer:
	@echo "Building NSIS installer..."
	makensis installer.nsi
	@echo "Output: dist/ZAI-Coder-1.23.0-Setup.exe"

docker-build:
	docker build -t zaicoder:latest .

docker-run:
	docker run --rm -e ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} zaicoder:latest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml dist build build-venv
