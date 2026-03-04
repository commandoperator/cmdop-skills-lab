PYTHON := uv run python

.PHONY: help install install-skill publish release test lint

help:
	@echo "llm-html"
	@echo ""
	@echo "  make install        Install from PyPI"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linter"
	@echo "  make install-skill  Register skill via cmdop-skill install"
	@echo "  make publish        Publish skill to CMDOP marketplace"
	@echo "  make release        Bump + build + upload to PyPI + CMDOP"

install:
	pip install -e .

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
