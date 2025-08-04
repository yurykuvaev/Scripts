.PHONY: help install fmt lint type test all clean

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install runtime + dev dependencies.
	pip install -r requirements.txt
	pip install ruff mypy pytest

fmt: ## Auto-format with ruff.
	ruff format .

lint: ## Lint with ruff.
	ruff check .

type: ## Type-check with mypy (informational).
	mypy --explicit-package-bases _common.py

test: ## Run pytest.
	pytest

all: lint type test ## Lint + type-check + test.

clean: ## Remove caches and build artifacts.
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__ */__pycache__
