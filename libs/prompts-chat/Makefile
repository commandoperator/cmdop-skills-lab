PYTHON := uv run --python .venv python

.PHONY: help install test lint install-skill publish release

help:
	@echo "prompts-chat"
	@echo ""
	@echo "  make install        Create venv and install in development mode"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linter"
	@echo "  make install-skill  Register skill via cmdop-skill install"
	@echo "  make publish        Publish skill to CMDOP marketplace"
	@echo "  make release        Bump + build + upload to PyPI"

install:
	uv venv
	uv pip install --python .venv -e '.[dev]'

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/

install-skill:
	cmdop-skill install .

publish:
	cmdop-skill publish --path .

release:
	cmdop-skill release .
