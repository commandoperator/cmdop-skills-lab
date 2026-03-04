.PHONY: help install test test-v test-cov lint dashboard send seed health accounts status stats release

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

install: ## Install package in dev mode
	pip install -e ".[dev,interactive]"

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run tests
	python -m pytest tests/

test-v: ## Run tests (verbose)
	python -m pytest tests/ -v

test-cov: ## Run tests with coverage
	python -m pytest tests/ -v --cov=src/llm_email --cov-report=term-missing

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

lint: ## Type-check with pyright
	pyright src/

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

dashboard: ## Launch Streamlit dashboard
	email-dashboard

dashboard-port: ## Launch dashboard on port 8502
	streamlit run src/llm_email/dashboard/app.py --server.port 8502

# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------

send: ## Send email (interactive prompts)
	python scripts/send.py send

send-draft: ## Create draft (interactive prompts)
	python scripts/send.py send --draft

send-accounts: ## List Mail.app accounts
	python scripts/send.py accounts

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

seed: ## Seed DB with 50 test records
	python scripts/seed.py

seed-clear: ## Clear DB and seed 50 fresh records
	python scripts/seed.py --clear

# ---------------------------------------------------------------------------
# Skill commands (quick checks)
# ---------------------------------------------------------------------------

health: ## Check Mail.app availability
	python run.py health

accounts: ## List Mail.app accounts
	python run.py accounts

status: ## Show recent sent emails
	python run.py status

stats: ## Show email statistics
	python run.py stats

# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------

release: ## Build and publish to PyPI
	python -m build
	twine upload dist/*
