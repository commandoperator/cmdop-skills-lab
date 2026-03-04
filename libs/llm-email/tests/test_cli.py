"""Tests for CLI dispatch (run.py)."""

from unittest import mock

import pytest

import run as run_module
from conftest import ExitCalled, mock_osascript


class TestCLI:
    """Test CLI dispatch via main_async (avoids asyncio.run nesting)."""

    @pytest.mark.asyncio
    async def test_health_subcommand(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout="true\n")):
            with mock.patch("sys.argv", ["run.py", "health"]):
                args = run_module.parse_args()
                with pytest.raises(ExitCalled) as exc_info:
                    await run_module.main_async(args)
        assert exc_info.value.output["ok"] is True

    @pytest.mark.asyncio
    async def test_status_subcommand(self) -> None:
        with mock.patch("sys.argv", ["run.py", "status"]):
            args = run_module.parse_args()
            with pytest.raises(ExitCalled) as exc_info:
                await run_module.main_async(args)
        assert exc_info.value.output["total_sent"] == 0

    @pytest.mark.asyncio
    async def test_accounts_subcommand(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout="Test|t@t.com\n")):
            with mock.patch("sys.argv", ["run.py", "accounts"]):
                args = run_module.parse_args()
                with pytest.raises(ExitCalled) as exc_info:
                    await run_module.main_async(args)
        assert len(exc_info.value.output["accounts"]) == 1

    @pytest.mark.asyncio
    async def test_send_subcommand(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            with mock.patch("sys.argv", [
                "run.py", "send",
                "--to", "x@y.com",
                "--subject", "Test",
                "--body", "Body text",
            ]):
                args = run_module.parse_args()
                with pytest.raises(ExitCalled) as exc_info:
                    await run_module.main_async(args)
        assert exc_info.value.output["action"] == "send"

    @pytest.mark.asyncio
    async def test_draft_subcommand(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            with mock.patch("sys.argv", [
                "run.py", "draft",
                "--to", "x@y.com",
                "--subject", "Draft",
                "--body", "Body",
            ]):
                args = run_module.parse_args()
                with pytest.raises(ExitCalled) as exc_info:
                    await run_module.main_async(args)
        assert exc_info.value.output["action"] == "draft"

    @pytest.mark.asyncio
    async def test_stats_subcommand(self) -> None:
        with mock.patch("sys.argv", ["run.py", "stats"]):
            args = run_module.parse_args()
            with pytest.raises(ExitCalled) as exc_info:
                await run_module.main_async(args)
        assert exc_info.value.output["total_sent"] == 0

    def test_no_subcommand_exits(self) -> None:
        with mock.patch("sys.argv", ["run.py"]):
            with pytest.raises(SystemExit) as exc_info:
                run_module.main()
        assert exc_info.value.code == 1
