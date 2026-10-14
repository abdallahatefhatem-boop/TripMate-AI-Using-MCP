VENV := .venv
BIN := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/,)

.PHONY: help install lint format test run docker-build docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  make install       - Install project dependencies with uv/pip"
	@echo "  make lint          - Run Ruff linter"
	@echo "  make format        - Format code with Ruff"
	@echo "  make test          - Run pytest test suite"
	@echo "  make run           - Run FastAPI application with Uvicorn"
	@echo "  make docker-build  - Build Docker container image"
	@echo "  make docker-up     - Start services with docker-compose"
	@echo "  make docker-down   - Stop docker-compose services"
	@echo "  make clean         - Remove pycache and temporary files"

install:
	$(BIN)pip install -e .

lint:
	$(BIN)ruff check .

format:
	$(BIN)ruff format .

test:
	$(BIN)pytest -v tests/

run:
	$(BIN)uvicorn main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t tripmate-ai:latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache
