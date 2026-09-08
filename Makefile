.PHONY: help install dev test build clean

help:
	@echo "PC Assistant - Available Commands"
	@echo "===================================="
	@echo "make install      - Install dependencies"
	@echo "make dev          - Start development environment"
	@echo "make test         - Run tests"
	@echo "make build        - Build for production"
	@echo "make clean        - Clean build artifacts"
	@echo "make lint         - Run linting"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	./start-dev.sh

test:
	cd backend && python -m pytest

build:
	./start-production.sh

clean:
	rm -rf backend/venv
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf desktop/target
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:
	cd backend && pylint *.py
	cd frontend && npm run lint
