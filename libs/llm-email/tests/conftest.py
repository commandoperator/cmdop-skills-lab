"""Shared fixtures for llm-email tests.

All osascript calls are mocked — tests run on any platform without Mail.app.
Uses in-memory SQLite via Tortoise ORM.
"""

import subprocess
from unittest import mock

import pytest
import pytest_asyncio
from tortoise import Tortoise

import run as run_module


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ExitCalled(Exception):
    """Raised instead of sys.exit inside json_output."""
    def __init__(self, code: int, output: dict):
        self.code = code
        self.output = output


# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def _init_test_db():
    """Set up in-memory SQLite for each test, tear down after."""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["llm_email.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


# ---------------------------------------------------------------------------
# CLI fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _catch_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Intercept json_output so it raises instead of calling sys.exit."""
    def fake_json_output(ok: bool = True, **kwargs):
        result = {"ok": ok, **kwargs}
        raise ExitCalled(0 if ok else 1, result)
    monkeypatch.setattr(run_module, "json_output", fake_json_output)


@pytest.fixture(autouse=True)
def _skip_real_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent init_db/close_db from running (DB already initialized by fixture)."""
    async def noop(*_a, **_kw):
        pass
    monkeypatch.setattr(run_module, "init_db", noop)
    monkeypatch.setattr(run_module, "close_db", noop)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_osascript(stdout: str = "", returncode: int = 0, stderr: str = "") -> mock.MagicMock:
    """Create a mock for subprocess.run that simulates osascript."""
    m = mock.MagicMock()
    m.return_value = subprocess.CompletedProcess(
        args=["osascript", "-e", "..."],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )
    return m
