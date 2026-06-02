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
# Cron (bounce + reply scan + Telegram notifications)
# ---------------------------------------------------------------------------

CRON_SCRIPT := $(CURDIR)/scripts/bounce_cron.py
CRON_PYTHONPATH := $(CURDIR)/src
CRON_LOG := $(CURDIR)/data/logs/bounce-cron.log
CRON_PYTHON := /opt/homebrew/opt/python@3.10/libexec/bin/python3
CRON_INTERVAL := 47 * * * *

cron-install: ## Install hourly bounce+reply scan to crontab
	@mkdir -p $(CURDIR)/data/logs
	@(crontab -l 2>/dev/null | grep -v 'bounce_cron.py'; \
	  echo "# llm-email: bounce + reply scan (hourly)"; \
	  echo "$(CRON_INTERVAL) cd $(CURDIR) && PYTHONPATH=$(CRON_PYTHONPATH) PYTHONUNBUFFERED=1 $(CRON_PYTHON) -u $(CRON_SCRIPT) --days 1 >> $(CRON_LOG) 2>&1") | crontab -
	@echo "Cron installed. Log: $(CRON_LOG)"
	@echo "Run 'make cron-status' to verify."

cron-remove: ## Remove bounce+reply scan from crontab
	@crontab -l 2>/dev/null | grep -v 'bounce_cron.py' | grep -v '# llm-email' | crontab - 2>/dev/null || true
	@echo "Cron removed."

cron-status: ## Show llm-email cron entries
	@crontab -l 2>/dev/null | grep -A1 'llm-email' || echo "No llm-email cron entries."

cron-log: ## Tail the bounce/reply scan log
	@tail -30 $(CRON_LOG) 2>/dev/null || echo "No log yet. Run 'make cron-install' first."

cron-run: ## Run bounce+reply scan now (manually)
	PYTHONPATH=$(CRON_PYTHONPATH) $(CRON_PYTHON) $(CRON_SCRIPT) --days 1

# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------

release: ## Release via CMDOP skill registry
	cmdop-skill release .
