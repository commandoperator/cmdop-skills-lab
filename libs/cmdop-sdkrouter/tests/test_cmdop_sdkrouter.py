"""Tests for cmdop-sdkrouter skill."""

from __future__ import annotations

import pytest

from cmdop_skill import TestClient

from cmdop_sdkrouter._skill import skill


@pytest.fixture
def client() -> TestClient:
    return TestClient(skill)


class TestSkillMeta:
    def test_skill_name(self) -> None:
        assert skill.name == "cmdop-sdkrouter"

    def test_skill_has_commands(self) -> None:
        assert len(skill.commands) > 50

    def test_command_names(self) -> None:
        names = {cmd.name for cmd in skill.commands}
        expected = {
            "chat", "chat-stream",
            "vision-analyze", "vision-ocr", "vision-models",
            "audio-transcribe", "audio-speech", "audio-speech-stream",
            "image-generate", "image-generate-async", "image-wait",
            "image-list", "image-get", "image-options",
            "search", "search-fetch", "search-async", "search-list",
            "cdn-upload", "cdn-get", "cdn-list", "cdn-delete", "cdn-stats",
            "translate", "translate-json", "detect-language", "translate-stats",
            "balance", "currencies", "deposit-estimate",
            "payment-create", "payment-status", "transactions",
            "withdrawal-create", "withdrawals",
            "proxy-list", "proxy-get", "proxy-create", "proxy-update",
            "proxy-delete", "proxy-healthy", "proxy-test",
            "shortlink-create", "shortlink-get", "shortlink-list", "shortlink-delete",
            "key-create", "key-list", "key-get", "key-rotate", "key-delete",
            "models-list", "models-get", "models-cost", "models-providers",
            "clean-html",
            "parse",
        }
        assert expected.issubset(names), f"Missing: {expected - names}"
