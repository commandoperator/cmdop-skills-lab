"""Tests for llm_email.mailer module."""

import subprocess
from unittest import mock

import pytest

from llm_email import mailer
from llm_email.models import SentEmail
from conftest import mock_osascript


class TestCheckHealth:
    def test_mail_running(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout="true\n")):
            result = mailer.check_health()
        assert result["ok"] is True
        assert result["mail_running"] is True

    def test_mail_not_running(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout="false\n")):
            result = mailer.check_health()
        assert result["ok"] is True
        assert result["mail_running"] is False

    def test_osascript_fails(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(returncode=1, stderr="no access")):
            result = mailer.check_health()
        assert result["ok"] is False
        assert "no access" in result["error"]


class TestListAccounts:
    @pytest.mark.asyncio
    async def test_parses_accounts(self) -> None:
        output = "iCloud|user@icloud.com\nGmail|user@gmail.com\n"
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout=output)):
            result = await mailer.list_accounts()
        assert result["ok"] is True
        assert len(result["accounts"]) == 2
        assert result["accounts"][0]["name"] == "iCloud"
        assert result["accounts"][0]["email"] == "user@icloud.com"
        assert result["accounts"][0]["default"] is True
        assert result["accounts"][1]["default"] is False

    @pytest.mark.asyncio
    async def test_fallback_email_only(self) -> None:
        output = "user@icloud.com\n"
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout=output)):
            result = await mailer.list_accounts()
        assert result["ok"] is True
        assert result["accounts"][0]["email"] == "user@icloud.com"

    @pytest.mark.asyncio
    async def test_empty(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(stdout="\n")):
            result = await mailer.list_accounts()
        assert result["ok"] is True
        assert result["accounts"] == []

    @pytest.mark.asyncio
    async def test_osascript_fails(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(returncode=1, stderr="denied")):
            result = await mailer.list_accounts()
        assert result["ok"] is False


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_send_builds_correct_script(self) -> None:
        captured_scripts: list[str] = []

        def fake_run(args, **kwargs):
            captured_scripts.append(args[2])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        with mock.patch("llm_email.applescript.subprocess.run", side_effect=fake_run):
            result = await mailer.send_email(to="test@example.com", subject="Hi", body="Hello there")

        assert result["ok"] is True
        assert result["action"] == "send"

        script = captured_scripts[0]
        assert 'tell application "Mail"' in script
        assert "send newMessage" in script
        assert "visible:false" in script
        assert 'address:"test@example.com"' in script
        assert 'subject:"Hi"' in script

    @pytest.mark.asyncio
    async def test_draft_no_send_command(self) -> None:
        captured_scripts: list[str] = []

        def fake_run(args, **kwargs):
            captured_scripts.append(args[2])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        with mock.patch("llm_email.applescript.subprocess.run", side_effect=fake_run):
            result = await mailer.send_email(
                to="test@example.com", subject="Hi", body="Hello", draft_only=True,
            )

        assert result["action"] == "draft"
        script = captured_scripts[0]
        assert "send newMessage" not in script
        assert "visible:true" in script

    @pytest.mark.asyncio
    async def test_send_with_cc_bcc(self) -> None:
        captured_scripts: list[str] = []

        def fake_run(args, **kwargs):
            captured_scripts.append(args[2])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        with mock.patch("llm_email.applescript.subprocess.run", side_effect=fake_run):
            await mailer.send_email(to="a@b.com", subject="S", body="B", cc="cc@b.com", bcc="bcc@b.com")

        script = captured_scripts[0]
        assert "cc recipient" in script
        assert "bcc recipient" in script
        assert 'address:"cc@b.com"' in script
        assert 'address:"bcc@b.com"' in script

    @pytest.mark.asyncio
    async def test_send_with_from_account(self) -> None:
        captured_scripts: list[str] = []

        def fake_run(args, **kwargs):
            captured_scripts.append(args[2])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        with mock.patch("llm_email.applescript.subprocess.run", side_effect=fake_run):
            await mailer.send_email(to="a@b.com", subject="S", body="B", from_account="me@gmail.com")

        script = captured_scripts[0]
        assert 'account "me@gmail.com"' in script
        assert "senderAddr" in script

    @pytest.mark.asyncio
    async def test_send_saves_to_db(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            await mailer.send_email(to="a@b.com", subject="Logged", body="Body")

        record = await SentEmail.first()
        assert record is not None
        assert record.to_addr == "a@b.com"
        assert record.subject == "Logged"
        assert record.action == "send"
        assert record.status == "ok"

    @pytest.mark.asyncio
    async def test_draft_saves_to_db(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            await mailer.send_email(to="a@b.com", subject="Draft", body="Body", draft_only=True)

        record = await SentEmail.first()
        assert record is not None
        assert record.action == "draft"
        assert record.status == "ok"

    @pytest.mark.asyncio
    async def test_send_failure_saves_error(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(returncode=1, stderr="Mail error")):
            result = await mailer.send_email(to="a@b.com", subject="Fail", body="Body")

        assert result["ok"] is False
        assert "Mail error" in result["error"]

        record = await SentEmail.first()
        assert record is not None
        assert record.status == "error"
        assert "Mail error" in record.error_message

    @pytest.mark.asyncio
    async def test_multiple_recipients(self) -> None:
        captured_scripts: list[str] = []

        def fake_run(args, **kwargs):
            captured_scripts.append(args[2])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        with mock.patch("llm_email.applescript.subprocess.run", side_effect=fake_run):
            await mailer.send_email(to="a@b.com, c@d.com", subject="S", body="B")

        script = captured_scripts[0]
        assert 'address:"a@b.com"' in script
        assert 'address:"c@d.com"' in script

    @pytest.mark.asyncio
    async def test_special_chars_in_body(self) -> None:
        captured_scripts: list[str] = []

        def fake_run(args, **kwargs):
            captured_scripts.append(args[2])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        with mock.patch("llm_email.applescript.subprocess.run", side_effect=fake_run):
            await mailer.send_email(to="a@b.com", subject='Say "hi"', body='Line1\nLine2\t"end"')

        script = captured_scripts[0]
        assert '\\"hi\\"' in script
        assert "\\n" in script
        assert "\\t" in script


class TestShowStatus:
    @pytest.mark.asyncio
    async def test_empty(self) -> None:
        result = await mailer.show_status()
        assert result["ok"] is True
        assert result["total_sent"] == 0
        assert result["recent"] == []

    @pytest.mark.asyncio
    async def test_with_entries(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            await mailer.send_email(to="a@b.com", subject="Test 1", body="B")
            await mailer.send_email(to="c@d.com", subject="Test 2", body="B")

        result = await mailer.show_status()
        assert result["total_sent"] == 2
        assert len(result["recent"]) == 2


class TestShowStats:
    @pytest.mark.asyncio
    async def test_empty_stats(self) -> None:
        result = await mailer.show_stats()
        assert result["ok"] is True
        assert result["total_sent"] == 0
        assert result["sent_today"] == 0
        assert result["sent_this_week"] == 0
        assert result["total_errors"] == 0
        assert result["top_recipients"] == []

    @pytest.mark.asyncio
    async def test_stats_with_data(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            await mailer.send_email(to="a@b.com", subject="S1", body="B")
            await mailer.send_email(to="a@b.com", subject="S2", body="B")
            await mailer.send_email(to="c@d.com", subject="S3", body="B")

        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript(returncode=1, stderr="err")):
            await mailer.send_email(to="e@f.com", subject="S4", body="B")

        result = await mailer.show_stats()
        assert result["total_sent"] == 3
        assert result["total_errors"] == 1
        assert len(result["top_recipients"]) >= 1
        assert result["top_recipients"][0]["to"] == "a@b.com"
        assert result["top_recipients"][0]["count"] == 2


class TestCheckDuplicate:
    @pytest.mark.asyncio
    async def test_no_duplicate(self) -> None:
        assert await mailer.check_duplicate("a@b.com", "Hello") is False

    @pytest.mark.asyncio
    async def test_duplicate_found(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            await mailer.send_email(to="a@b.com", subject="Hello", body="B")

        assert await mailer.check_duplicate("a@b.com", "Hello") is True

    @pytest.mark.asyncio
    async def test_different_subject_not_duplicate(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            await mailer.send_email(to="a@b.com", subject="Hello", body="B")

        assert await mailer.check_duplicate("a@b.com", "Different") is False

    @pytest.mark.asyncio
    async def test_draft_not_counted(self) -> None:
        with mock.patch("llm_email.applescript.subprocess.run", mock_osascript()):
            await mailer.send_email(to="a@b.com", subject="Hello", body="B", draft_only=True)

        assert await mailer.check_duplicate("a@b.com", "Hello") is False
