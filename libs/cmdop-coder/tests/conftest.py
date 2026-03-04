"""Shared fixtures for cmdop-coder tests."""

import textwrap
from pathlib import Path

import pytest
from cmdop_skill import TestClient

from cmdop_coder._skill import skill


@pytest.fixture
def client() -> TestClient:
    return TestClient(skill)


@pytest.fixture
def write_src(tmp_path: Path):
    """Factory: write a dedented source file and return its Path."""
    def _write(name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(textwrap.dedent(content))
        return p
    return _write
