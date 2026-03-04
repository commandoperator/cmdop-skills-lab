"""Tests for hello-world skill."""

from __future__ import annotations

import pytest

from cmdop_skill import TestClient

from hello_world._skill import skill


@pytest.fixture
def client() -> TestClient:
    return TestClient(skill)


class TestGreet:
    async def test_greet_basic(self, client: TestClient) -> None:
        result = await client.run("greet", name="Alice", shout=False)
        assert result["ok"] is True
        assert result["message"] == "Hello, Alice!"

    async def test_greet_shout(self, client: TestClient) -> None:
        result = await client.run_cli("greet", "--name", "Bob", "--shout")
        assert result["ok"] is True
        assert result["message"] == "HELLO, BOB!"


class TestGoodbye:
    async def test_goodbye(self, client: TestClient) -> None:
        result = await client.run("goodbye", name="Charlie")
        assert result["ok"] is True
        assert result["message"] == "Goodbye, Charlie!"
