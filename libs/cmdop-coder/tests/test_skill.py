"""Tests for skill commands via TestClient."""

import textwrap
from pathlib import Path

import pytest
from cmdop_skill import TestClient

from cmdop_coder._skill import skill


@pytest.fixture
def client() -> TestClient:
    return TestClient(skill)


def src(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content))
    return p


class TestFunctionsCommand:
    async def test_returns_ok(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "def hello(): pass\n")
        result = await client.run("functions", path=str(f))
        assert result["ok"] is True
        assert result["count"] == 1
        assert result["language"] == "python"

    async def test_functions_list_structure(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "def foo(): pass\ndef bar(): pass\n")
        result = await client.run("functions", path=str(f))
        assert result["ok"] is True
        assert len(result["functions"]) == 2
        fn = result["functions"][0]
        assert "line" in fn
        assert "name" in fn
        assert "signature" in fn

    async def test_missing_path_returns_error(self, client: TestClient) -> None:
        result = await client.run("functions")
        assert result["ok"] is False

    async def test_via_cli(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "def hello(): pass\n")
        result = await client.run_cli("functions", "--path", str(f))
        assert result["ok"] is True
        assert result["count"] == 1


class TestSymbolsCommand:
    async def test_finds_symbol(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "MY_CONST = 1\nx = MY_CONST\n")
        result = await client.run("symbols", symbol="MY_CONST", path=str(f))
        assert result["ok"] is True
        assert result["count"] == 2
        assert result["symbol"] == "MY_CONST"

    async def test_not_found_returns_empty(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "x = 1\n")
        result = await client.run("symbols", symbol="MISSING", path=str(f))
        assert result["ok"] is True
        assert result["count"] == 0
        assert result["matches"] == []

    async def test_missing_symbol_returns_error(self, client: TestClient) -> None:
        result = await client.run("symbols")
        assert result["ok"] is False

    async def test_via_cli(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "TARGET = 1\n")
        result = await client.run_cli("symbols", "--symbol", "TARGET", "--path", str(f))
        assert result["ok"] is True
        assert result["count"] == 1


class TestOutlineCommand:
    async def test_returns_ok(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "mod.py", "import os\nclass Foo: pass\n")
        result = await client.run("outline", path=str(f))
        assert result["ok"] is True
        assert result["language"] == "python"
        assert isinstance(result["outline"], list)
        assert result["count"] > 0

    async def test_outline_items_have_required_fields(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "mod.py", "import os\n")
        result = await client.run("outline", path=str(f))
        assert result["ok"] is True
        for item in result["outline"]:
            assert "line" in item
            assert "type" in item
            assert "name" in item

    async def test_missing_path_returns_error(self, client: TestClient) -> None:
        result = await client.run("outline")
        assert result["ok"] is False


class TestAnalyzeCommand:
    async def test_returns_ok(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "script.py", "# comment\ndef main(): pass\nmain()\n")
        result = await client.run("analyze", path=str(f))
        assert result["ok"] is True
        assert result["language"] == "python"
        assert result["total_lines"] == 3
        assert result["function_count"] == 1

    async def test_line_counts_sum(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "# c\nimport os\n\ndef foo(): pass\n")
        result = await client.run("analyze", path=str(f))
        assert result["ok"] is True
        total = result["blank_lines"] + result["code_lines"] + result["comment_lines"]
        assert total == result["total_lines"]

    async def test_unknown_extension(self, client: TestClient, tmp_path: Path) -> None:
        f = tmp_path / "data.xyz"
        f.write_text("hello\nworld\n")
        result = await client.run("analyze", path=str(f))
        assert result["ok"] is True
        assert result["language"] == "unknown"
        assert result["function_count"] is None

    async def test_missing_path_returns_error(self, client: TestClient) -> None:
        result = await client.run("analyze")
        assert result["ok"] is False

    async def test_via_cli(self, client: TestClient, tmp_path: Path) -> None:
        f = src(tmp_path, "x.go", "package main\nfunc main() {}\n")
        result = await client.run_cli("analyze", "--path", str(f))
        assert result["ok"] is True
        assert result["language"] == "go"
