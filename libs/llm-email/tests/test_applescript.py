"""Tests for llm_email.applescript module."""

import subprocess
from unittest import mock

from llm_email import applescript
from conftest import mock_osascript


class TestEscapeAppleScript:
    def test_plain_text(self) -> None:
        assert applescript.escape_applescript("hello world") == "hello world"

    def test_double_quotes(self) -> None:
        assert applescript.escape_applescript('say "hi"') == 'say \\"hi\\"'

    def test_backslash(self) -> None:
        assert applescript.escape_applescript("path\\to") == "path\\\\to"

    def test_newline(self) -> None:
        assert applescript.escape_applescript("line1\nline2") == "line1\\nline2"

    def test_carriage_return(self) -> None:
        assert applescript.escape_applescript("a\rb") == "a\\rb"

    def test_tab(self) -> None:
        assert applescript.escape_applescript("a\tb") == "a\\tb"

    def test_combined(self) -> None:
        result = applescript.escape_applescript('He said "hello"\nand\tleft\\')
        assert result == 'He said \\"hello\\"\\nand\\tleft\\\\'

    def test_empty(self) -> None:
        assert applescript.escape_applescript("") == ""


class TestSplitAddrs:
    def test_single(self) -> None:
        assert applescript.split_addrs("a@b.com") == ["a@b.com"]

    def test_multiple(self) -> None:
        assert applescript.split_addrs("a@b.com, c@d.com") == ["a@b.com", "c@d.com"]

    def test_empty(self) -> None:
        assert applescript.split_addrs("") == []

    def test_whitespace(self) -> None:
        assert applescript.split_addrs("  a@b.com , , c@d.com  ") == ["a@b.com", "c@d.com"]

    def test_trailing_comma(self) -> None:
        assert applescript.split_addrs("a@b.com,") == ["a@b.com"]


class TestRunOsascript:
    def test_success(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout="ok\n")):
            ok, output = applescript.run_osascript("some script")
        assert ok is True
        assert output == "ok"

    def test_failure(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(returncode=1, stderr="err msg")):
            ok, output = applescript.run_osascript("bad script")
        assert ok is False
        assert output == "err msg"

    def test_timeout(self) -> None:
        m = mock.MagicMock(side_effect=subprocess.TimeoutExpired(cmd="osascript", timeout=30))
        with mock.patch("llm_email.applescript.subprocess.run", m):
            ok, output = applescript.run_osascript("slow script", timeout=1)
        assert ok is False
        assert "timed out" in output

    def test_not_found(self) -> None:
        m = mock.MagicMock(side_effect=FileNotFoundError)
        with mock.patch("llm_email.applescript.subprocess.run", m):
            ok, output = applescript.run_osascript("any")
        assert ok is False
        assert "not found" in output
