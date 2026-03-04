PYTHON := uv run python

.PHONY: help install dev test lint format clean install-skill publish release

help:
	@echo "cmdop-sdkrouter"
	@echo ""
	@echo "  make install        Install from PyPI"
	@echo "  make dev            Install with dev dependencies"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linter"
	@echo "  make format         Run formatter"
	@echo "  make clean          Remove build artifacts"
	@echo "  make install-skill  Register skill via cmdop-skill install"
	@echo "  make publish        Publish skill to CMDOP marketplace"
	@echo "  make release        Bump + build + upload to PyPI + CMDOP"

install:
	pip install -e .

dev:
	pip install -e '.[dev]'

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

install-skill:
	cmdop-skill install .

publish:
	cmdop-skill publish --path .

release:
	cmdop-skill release .
