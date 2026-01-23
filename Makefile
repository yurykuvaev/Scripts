.PHONY: help install fmt lint type test all clean cleanup-report cleanup-amis cleanup-sgs

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-22s %s\n", $$1, $$2}'

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

# --- AWS cleanup shortcuts ---------------------------------------------------
# Each target is read-only by default; pass DELETE=1 to actually remove things.

cleanup-report: ## Run all cleanup scripts in report mode (no AWS writes).
	@echo "==> unused security groups"
	@python unused_security_groups.py
	@echo "==> stale AMIs"
	@python ami_cleanup.py

cleanup-amis: ## Deregister unused AMIs. DELETE=1 to actually remove (else dry-run).
	python ami_cleanup.py --delete $(if $(DELETE),,--dry-run)

cleanup-sgs: ## Delete unused security groups. DELETE=1 to actually remove (else dry-run).
	python unused_security_groups.py --delete $(if $(DELETE),,--dry-run)
